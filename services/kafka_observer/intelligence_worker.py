"""Continuous, renewable-lease worker for Stream Intelligence."""

from __future__ import annotations

import logging
import random
import time
from datetime import datetime, timedelta, timezone

from services.kafka_observer.reliability_runtime import StaleWriter

log = logging.getLogger(__name__)


class IntelligenceWorker:
    def __init__(
        self,
        runtime: object,
        tenant: str,
        environment: str,
        *,
        interval_seconds: float = 30,
        maximum_backoff_seconds: float = 120,
    ):
        self.runtime, self.tenant, self.environment = runtime, tenant, environment
        self.interval_seconds = max(0.1, interval_seconds)
        self.maximum_backoff_seconds = max(self.interval_seconds, maximum_backoff_seconds)
        self.stopping = False

    def stop(self) -> None:
        self.stopping = True
        self.runtime.stop()

    def run(self) -> None:
        failures = 0
        while not self.stopping:
            try:
                completed = self.runtime.run_once(self.tenant, self.environment)
                failures = 0
                log.info(
                    "stream_intelligence_cycle",
                    extra={"tenant": self.tenant, "environment": self.environment, "evaluated": len(completed)},
                )
                delay = self.interval_seconds
            except StaleWriter:
                log.warning(
                    "stream_intelligence_lease_lost", extra={"tenant": self.tenant, "environment": self.environment}
                )
                break  # stop mutations immediately; process manager may create a fresh worker
            except Exception:
                failures += 1
                delay = min(self.maximum_backoff_seconds, self.interval_seconds * (2 ** min(failures, 8)))
                delay += random.uniform(0, delay * 0.2)
                log.exception(
                    "stream_intelligence_cycle_failed",
                    extra={"tenant": self.tenant, "environment": self.environment, "attempt": failures},
                )
            time.sleep(delay)
