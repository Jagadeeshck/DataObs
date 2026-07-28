"""One bounded schedule execution with lease fencing."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from hashlib import sha256

from packages.domain_model.monitor import ColdStartState, MonitorEvaluation, MonitorObservation
from services.monitoring.baseline_service import build_baseline
from services.monitoring.evaluation_service import evaluate
from services.monitoring.providers.base import ProviderBudget


class MonitorWorker:
    def __init__(self, repo, providers, *, owner: str, lease_seconds: int = 30):
        self.repo = repo
        self.providers = providers
        self.owner = owner
        self.lease_seconds = lease_seconds

    def execute(self, schedule: dict):
        now = datetime.now(timezone.utc)
        scope = (schedule["tenant_id"], schedule["environment"])
        monitor_id = schedule["monitor_id"]
        lease = self.repo.acquire_lease(
            *scope, monitor_id, self.owner, now, now + timedelta(seconds=self.lease_seconds)
        )
        if not lease:
            return "contended"
        try:
            monitor = self.repo.get_monitor(*scope, monitor_id)
            provider = self.providers.resolve(monitor.monitor_type.value)
            result = provider.observe(*scope, monitor.target.model_dump(mode="json"), ProviderBudget())
            observation = MonitorObservation(
                monitor_id=monitor_id,
                tenant_id=scope[0],
                environment=scope[1],
                observed_at=result.observed_at,
                value=result.value,
                sample_count=result.sample_count,
                missing_data=result.missing_data,
                dimensions=result.dimensions,
            )
            self.repo.append_observation(observation)
            history = self.repo.history(
                *scope, monitor_id, now, monitor.baseline.history_points if monitor.baseline else 168
            )
            baseline = build_baseline(
                tenant_id=scope[0],
                environment=scope[1],
                monitor_id=monitor_id,
                definition_revision=monitor.revision,
                observations=history,
            )
            self.repo.create_baseline_version(baseline)
            decision = evaluate(monitor, observation, baseline, provider_status=result.provider_status)
            evaluation_id = sha256(f"{scope[0]}\0{scope[1]}\0{monitor_id}\0{now.isoformat()}".encode()).hexdigest()
            evaluation = MonitorEvaluation(
                evaluation_id=evaluation_id,
                monitor_id=monitor_id,
                tenant_id=scope[0],
                environment=scope[1],
                definition_revision=monitor.revision,
                baseline_version=decision.get("baseline_version"),
                observation=observation,
                expected_minimum=(baseline or {}).get("expected_minimum", monitor.threshold.minimum),
                expected_maximum=(baseline or {}).get("expected_maximum", monitor.threshold.maximum),
                method=(monitor.baseline.method if monitor.baseline else "fixed"),
                sensitivity=(monitor.baseline.sensitivity if monitor.baseline else "fixed"),
                threshold_calculation=",".join(decision["reason_codes"]),
                sample_count=observation.sample_count,
                confidence=result.confidence,
                cold_start_state=(baseline or {}).get("cold_start_state", ColdStartState.COLLECTING),
                missing_inputs=decision["missing_inputs"],
                breached=decision["state"] == "breached",
            )
            self.repo.save_evaluation(evaluation, idempotency_key=evaluation.evaluation_id)
            self.repo.checkpoint(
                *scope,
                monitor_id,
                {
                    "last_execution_at": now.isoformat(),
                    "last_evaluation_id": evaluation.evaluation_id,
                    "fencing_owner": self.owner,
                },
                expected_revision=None,
            )
            match = re.fullmatch(r"([1-9][0-9]*)(m|h|d)", monitor.schedule.interval)
            if match:
                interval = timedelta(
                    **{
                        "m": {"minutes": int(match.group(1))},
                        "h": {"hours": int(match.group(1))},
                        "d": {"days": int(match.group(1))},
                    }[match.group(2)]
                )
                self.repo.save_schedule_state(
                    *scope,
                    monitor_id,
                    {
                        **schedule,
                        "state": "enabled",
                        "last_scheduled_for": schedule.get("next_scheduled_for", now.isoformat()),
                        "next_scheduled_for": (now + interval).isoformat(),
                        "execution_request": False,
                    },
                )
            return "breached" if evaluation.breached else "succeeded"
        finally:
            self.repo.release_lease(*scope, monitor_id, self.owner)
