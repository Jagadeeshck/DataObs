"""Redaction-safe runtime health contracts."""

from dataclasses import asdict, dataclass
from datetime import datetime


@dataclass
class RuntimeHealth:
    state: str = "idle"
    loop_started_at: datetime | None = None
    last_heartbeat_at: datetime | None = None
    last_successful_cycle_at: datetime | None = None
    last_failed_cycle_at: datetime | None = None
    consecutive_failures: int = 0
    jobs_processed: int = 0
    runs_processed: int = 0
    expected_runs_generated: int = 0
    late_runs_detected: int = 0
    missing_runs_detected: int = 0
    recovered_missing_runs: int = 0
    evaluations_written: int = 0
    snapshots_written: int = 0
    backlog: int = 0
    checkpoint_lag_seconds: float = 0
    active_leases: int = 0
    expired_leases: int = 0
    next_cycle_at: datetime | None = None

    def as_dict(self):
        return asdict(self)
