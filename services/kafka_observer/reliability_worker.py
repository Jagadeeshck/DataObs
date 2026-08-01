"""Continuous production loop around the canonical reliability runtime."""

from __future__ import annotations

import json
import random
import signal
import time
from datetime import datetime, timezone
from typing import Callable

from services.kafka_observer.reliability_runtime import ReliabilityRuntime, StaleWriter


class ReliabilityWorker:
    """Poll independently scoped definitions with bounded transient retries."""

    def __init__(
        self,
        runtime: ReliabilityRuntime,
        tenant: str,
        environment: str,
        *,
        poll_seconds: float = 30,
        maximum_retries: int = 4,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.runtime = runtime
        self.tenant = tenant
        self.environment = environment
        self.poll_seconds = max(1.0, min(poll_seconds, 300.0))
        self.maximum_retries = max(0, min(maximum_retries, 8))
        self.sleep = sleep
        self.stopping = False

    def stop(self, *_: object) -> None:
        self.stopping = True
        self.runtime.stop()

    def run(self) -> None:
        signal.signal(signal.SIGINT, self.stop)
        signal.signal(signal.SIGTERM, self.stop)
        while not self.stopping:
            self.run_cycle()
            if not self.stopping:
                self.sleep(self.poll_seconds)

    def run_cycle(self) -> None:
        for attempt in range(self.maximum_retries + 1):
            try:
                evaluations = self.runtime.run_once(self.tenant, self.environment)
                self._log("cycle_complete", evaluated=len(evaluations))
                return
            except StaleWriter:
                self._log("cycle_rejected", error_type="stale_writer")
                return
            except (ConnectionError, TimeoutError) as error:
                self.runtime.health.elasticsearch_status = "unavailable"
                self.runtime.health.latest_failed_evaluation = datetime.now(timezone.utc)
                self._log("cycle_retry", error_type=type(error).__name__, attempt=attempt + 1)
                if attempt == self.maximum_retries:
                    return
                self.sleep(min(30.0, (2**attempt) + random.uniform(0, 0.5)))

    def _log(self, event: str, **fields: object) -> None:
        # Only operational counts/categories are logged; definitions and evidence are intentionally excluded.
        print(json.dumps({"event": event, "worker_id": self.runtime.health.worker_id, **fields}, sort_keys=True))
