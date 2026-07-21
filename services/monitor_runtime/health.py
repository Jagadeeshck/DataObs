from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class RuntimeHealth:
    last_loop_started: datetime | None = None
    last_successful_cycle: datetime | None = None
    backlog: int = 0

    def snapshot(self, *, stuck_after_seconds: int = 120):
        now = datetime.now(timezone.utc)
        stuck = bool(
            self.last_loop_started
            and (now - self.last_loop_started).total_seconds() > stuck_after_seconds
            and (not self.last_successful_cycle or self.last_successful_cycle < self.last_loop_started)
        )
        return {
            "live": not stuck,
            "ready": self.last_successful_cycle is not None,
            "backlog": self.backlog,
            "last_successful_cycle": self.last_successful_cycle.isoformat() if self.last_successful_cycle else None,
        }
