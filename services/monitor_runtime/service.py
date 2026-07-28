from __future__ import annotations

import signal
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from services.monitor_runtime.health import RuntimeHealth


class MonitorRuntime:
    def __init__(self, repo, worker, *, tenant_id: str, environment: str, concurrency: int = 4, batch_size: int = 100):
        self.repo = repo
        self.worker = worker
        self.tenant_id = tenant_id
        self.environment = environment
        self.concurrency = min(max(concurrency, 1), 32)
        self.batch_size = min(max(batch_size, 1), 500)
        self.health = RuntimeHealth()
        self.stopping = False

    def once(self):
        self.health.last_loop_started = datetime.now(timezone.utc)
        due = self.repo.list_due_schedules(
            self.tenant_id, self.environment, self.health.last_loop_started, self.batch_size
        )
        self.health.backlog = len(due)
        with ThreadPoolExecutor(max_workers=self.concurrency) as pool:
            outcomes = list(pool.map(self.worker.execute, due))
        self.health.last_successful_cycle = datetime.now(timezone.utc)
        counts = {
            key: outcomes.count(key)
            for key in ("succeeded", "breached", "recovered", "suppressed", "retrying", "failed", "contended")
        }
        return {
            "due_monitors": len(due),
            "claimed_monitors": len(due) - counts["contended"],
            "executed_monitors": len(outcomes) - counts["contended"],
            **counts,
        }

    def run(self, interval=5):
        signal.signal(signal.SIGTERM, lambda *_: setattr(self, "stopping", True))
        signal.signal(signal.SIGINT, lambda *_: setattr(self, "stopping", True))
        while not self.stopping:
            self.once()
            deadline = time.monotonic() + interval
            while not self.stopping and time.monotonic() < deadline:
                time.sleep(min(0.25, deadline - time.monotonic()))
