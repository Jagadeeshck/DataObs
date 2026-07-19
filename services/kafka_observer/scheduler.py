from __future__ import annotations

import hashlib
import random
import threading
import time
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class ScheduledCollection:
    name: str
    interval_seconds: float
    collect: Callable[[], object]
    max_backoff_seconds: float = 300.0


class CollectionScheduler:
    """Cooperative, bounded scheduler; durable ownership is delegated to a lease store."""

    def __init__(self, jobs: list[ScheduledCollection], leases: object, owner: str, *, jitter: float = 0.1):
        self.jobs = jobs
        self.leases = leases
        self.owner = owner
        self.jitter = max(0.0, min(jitter, 0.5))
        self._stop = threading.Event()

    def stop(self) -> None:
        self._stop.set()

    def run(self) -> None:
        due = {job.name: time.monotonic() for job in self.jobs}
        failures = {job.name: 0 for job in self.jobs}
        while not self._stop.is_set():
            now = time.monotonic()
            for job in self.jobs:
                if now < due[job.name]:
                    continue
                if not self.leases.acquire(job.name, self.owner, max(job.interval_seconds * 2, 10)):
                    due[job.name] = now + min(job.interval_seconds, 5)
                    continue
                try:
                    job.collect()
                    failures[job.name] = 0
                except Exception:
                    failures[job.name] += 1
                finally:
                    self.leases.release(job.name, self.owner)
                backoff = min(job.max_backoff_seconds, job.interval_seconds * (2 ** failures[job.name]))
                seed = int(hashlib.sha256(f"{self.owner}:{job.name}".encode()).hexdigest()[:8], 16)
                noise = random.Random(seed + int(now)).uniform(-self.jitter, self.jitter)
                due[job.name] = now + max(0.1, backoff * (1 + noise))
            self._stop.wait(0.25)
