"""Bounded reliability cycle orchestration."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable

from .health import RuntimeHealth
from .repository import ReliabilityRepository
from .schedule import generate_expected_runs


@dataclass(frozen=True)
class CycleResult:
    partition: str
    started_at: datetime
    completed_at: datetime
    jobs_processed: int
    expected_runs_generated: int
    checkpoint_advanced: bool


class ReliabilityService:
    def __init__(
        self,
        repository: ReliabilityRepository,
        *,
        owner: str,
        batch_size: int = 100,
        overlap_seconds: int = 300,
        clock: Callable[[], datetime] | None = None,
    ):
        self.repository, self.owner = repository, owner
        self.batch_size, self.overlap_seconds = min(max(batch_size, 1), 1000), max(overlap_seconds, 0)
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.health = RuntimeHealth()

    def once(self, tenant_id: str, environment: str, job_ids: list[str]) -> CycleResult:
        started = self.clock()
        partition = f"{tenant_id}:{environment}"
        token = self.repository.claim_lease(partition, self.owner, started, 60)
        generated = processed = 0
        advanced = False
        try:
            checkpoint = self.repository.read_checkpoint(partition) or started - timedelta(seconds=self.overlap_seconds)
            for job_id in job_ids[: self.batch_size]:
                policy = self.repository.get_policy(tenant_id, environment, job_id)
                if not policy:
                    continue
                processed += 1
                for expected in generate_expected_runs(policy, checkpoint, started):
                    generated += int(self.repository.create_expected_run(expected))
            self.repository.update_checkpoint(partition, self.owner, token, started)
            advanced = True
            self.health.last_successful_cycle_at = self.clock()
            self.health.consecutive_failures = 0
        except Exception:
            self.health.last_failed_cycle_at = self.clock()
            self.health.consecutive_failures += 1
            raise
        finally:
            self.repository.release_lease(partition, self.owner, token)
        completed = self.clock()
        self.health.jobs_processed += processed
        self.health.expected_runs_generated += generated
        self.health.last_heartbeat_at = completed
        return CycleResult(partition, started, completed, processed, generated, advanced)
