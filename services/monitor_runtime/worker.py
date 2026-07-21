"""One bounded schedule execution with lease fencing."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from packages.domain_model.monitor import MonitorObservation
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
            return evaluate(monitor, observation, baseline, provider_status=result.provider_status)
        finally:
            self.repo.release_lease(*scope, monitor_id, self.owner)
