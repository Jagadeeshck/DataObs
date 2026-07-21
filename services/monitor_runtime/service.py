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
            list(pool.map(self.worker.execute, due))
        self.health.last_successful_cycle = datetime.now(timezone.utc)
        return len(due)

    def run(self, interval=5):
        signal.signal(signal.SIGTERM, lambda *_: setattr(self, "stopping", True))
        while not self.stopping:
            self.once()
            time.sleep(interval)
