from __future__ import annotations

import hashlib
import random
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
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
    max_retries: int = 5


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
        concurrency: int = 4,
        checkpoints: object | None = None,
    ):
        self.jobs = jobs
        self.leases = leases
        self.owner = owner
        self.jitter = max(0.0, min(jitter, 0.5))
        self.lease_seconds = max(10, lease_seconds)
        self.renewal_seconds = min(max(1, renewal_seconds), self.lease_seconds / 2)
        self.on_error = on_error
        self.concurrency = max(1, min(concurrency, 32))
        self.checkpoints = checkpoints
        self._stop = threading.Event()

    def stop(self) -> None:
        self._stop.set()

    def run(self) -> None:
        due = {job.name: time.monotonic() for job in self.jobs}
        failures = {job.name: 0 for job in self.jobs}
        active: dict[str, Future[None]] = {}

        def execute(job: ScheduledCollection) -> None:
            if not self.leases.acquire(job.name, self.owner, self.lease_seconds):
                raise LeaseUnavailable(job.name)
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
            finally:
                renewal_stop.set()
                renewer.join(timeout=self.renewal_seconds + 1)
                self.leases.release(job.name, self.owner)

        with ThreadPoolExecutor(max_workers=self.concurrency, thread_name_prefix="kafka-observer") as pool:
            while not self._stop.is_set():
                now = time.monotonic()
                for name, future in list(active.items()):
                    if not future.done():
                        continue
                    active.pop(name)
                    job = next(item for item in self.jobs if item.name == name)
                    try:
                        future.result()
                        failures[name] = 0
                    except LeaseUnavailable:
                        due[name] = now + min(job.interval_seconds, 5)
                        continue
                    except Exception as error:
                        failures[name] = min(failures[name] + 1, job.max_retries)
                        if self.on_error is not None:
                            self.on_error(name, error, failures[name])
                    backoff = min(job.max_backoff_seconds, job.interval_seconds * (2 ** failures[name]))
                    seed = int(hashlib.sha256(f"{self.owner}:{name}".encode()).hexdigest()[:8], 16)
                    noise = random.Random(seed + int(now)).uniform(-self.jitter, self.jitter)
                    due[name] = now + max(0.1, backoff * (1 + noise))
                for job in self.jobs:
                    if job.name not in active and now >= due[job.name] and len(active) < self.concurrency:
                        active[job.name] = pool.submit(execute, job)
                self._stop.wait(0.1)


class LeaseUnavailable(RuntimeError):
    """Another live observer owns this scoped capability."""
