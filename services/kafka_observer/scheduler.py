from __future__ import annotations

import hashlib
import random
import threading
import time
from dataclasses import dataclass
from typing import Callable, Protocol


class LeaseStore(Protocol):
    def acquire(self, name: str, owner: str, duration_seconds: float) -> bool: ...
    def renew(self, name: str, owner: str, duration_seconds: float) -> bool: ...
    def release(self, name: str, owner: str) -> None: ...


@dataclass(frozen=True)
class ScheduledCollection:
    name: str
    interval_seconds: float
    collect: Callable[[], object]
    max_backoff_seconds: float = 300.0


class CollectionScheduler:
    """Cooperative, bounded scheduler; durable ownership is delegated to a lease store."""

    def __init__(
        self,
        jobs: list[ScheduledCollection],
        leases: LeaseStore,
        owner: str,
        *,
        jitter: float = 0.1,
        lease_seconds: float = 60,
        renewal_seconds: float = 20,
        on_error: Callable[[str, Exception, int], None] | None = None,
    ):
        self.jobs = jobs
        self.leases = leases
        self.owner = owner
        self.jitter = max(0.0, min(jitter, 0.5))
        self.lease_seconds = max(10, lease_seconds)
        self.renewal_seconds = min(max(1, renewal_seconds), self.lease_seconds / 2)
        self.on_error = on_error
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
                if not self.leases.acquire(job.name, self.owner, self.lease_seconds):
                    due[job.name] = now + min(job.interval_seconds, 5)
                    continue
                renewal_stop = threading.Event()
                lease_lost = threading.Event()

                def renew() -> None:
                    while not renewal_stop.wait(self.renewal_seconds):
                        if not self.leases.renew(job.name, self.owner, self.lease_seconds):
                            lease_lost.set()
                            return

                renewer = threading.Thread(target=renew, name=f"lease-renew-{job.name}", daemon=True)
                renewer.start()
                try:
                    job.collect()
                    if lease_lost.is_set():
                        raise RuntimeError("collection lease was lost")
                    failures[job.name] = 0
                except Exception as error:
                    failures[job.name] += 1
                    if self.on_error is not None:
                        self.on_error(job.name, error, failures[job.name])
                finally:
                    renewal_stop.set()
                    renewer.join(timeout=self.renewal_seconds + 1)
                    self.leases.release(job.name, self.owner)
                backoff = min(job.max_backoff_seconds, job.interval_seconds * (2 ** failures[job.name]))
                seed = int(hashlib.sha256(f"{self.owner}:{job.name}".encode()).hexdigest()[:8], 16)
                noise = random.Random(seed + int(now)).uniform(-self.jitter, self.jitter)
                due[job.name] = now + max(0.1, backoff * (1 + noise))
            self._stop.wait(0.25)
