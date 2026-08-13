"""Bounded, fenced SLO evaluation cycle."""

from __future__ import annotations

import re
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from packages.domain_model.slo import evaluate_intervals


def duration(value: str) -> timedelta:
    amount, unit = re.fullmatch(r"(\d+)([mhd])", value).groups()
    return timedelta(**{{"m": "minutes", "h": "hours", "d": "days"}[unit]: int(amount)})


class DataSLORuntime:
    def __init__(self, repository, evidence_resolver, *, worker_id: str, lease_seconds: int = 60):
        self.repository, self.evidence_resolver, self.worker_id, self.lease_seconds = (
            repository,
            evidence_resolver,
            worker_id,
            lease_seconds,
        )

    def evaluate_due(self, tenant_id: str, environment: str, *, now=None, limit=100):
        now = now or datetime.now(timezone.utc)
        results = []
        for due in self.repository.list_due(tenant_id, environment, now, limit=min(limit, 200)):
            token = self.repository.acquire_lease(
                tenant_id, environment, due.slo_id, self.worker_id, now, now + timedelta(seconds=self.lease_seconds)
            )
            if token is None:
                continue
            definition = self.repository.get_definition(tenant_id, environment, due.slo_id)
            if definition is None or definition.state != "active":
                continue
            start = now - duration(definition.window)
            evidence = self.evidence_resolver.resolve(definition, start, now)
            evaluation = evaluate_intervals(definition, evidence, window_start=start, window_end=now, evaluated_at=now)
            self.repository.append_evaluation(evaluation)
            self.repository.put_current(evaluation, fencing_token=token)
            state = self.repository.get_runtime(tenant_id, environment, due.slo_id)
            self.repository.checkpoint(
                replace(
                    state,
                    next_evaluation_at=now + duration(definition.evaluation_granularity),
                    last_checkpoint=now,
                    last_success=now,
                    lease_owner=None,
                    lease_expires_at=None,
                ),
                fencing_token=token,
            )
            results.append(evaluation)
        return results
