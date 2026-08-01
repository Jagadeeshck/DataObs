from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass
from time import monotonic
from typing import Awaitable, Callable, TypeVar

from .errors import IntegrationError

T = TypeVar("T")


@dataclass(frozen=True)
class RetryPolicy:
    maximum_attempts: int = 3
    maximum_elapsed_seconds: float = 30.0
    base_delay_seconds: float = 0.25
    maximum_delay_seconds: float = 5.0
    jitter_ratio: float = 0.2

    def __post_init__(self) -> None:
        if not 1 <= self.maximum_attempts <= 10:
            raise ValueError("maximum_attempts must be between 1 and 10")
        if self.maximum_elapsed_seconds <= 0 or self.base_delay_seconds < 0:
            raise ValueError("retry durations must be bounded and non-negative")


async def with_retry(
    operation: Callable[[], Awaitable[T]],
    policy: RetryPolicy,
    *,
    random_source: random.Random | None = None,
    on_retry: Callable[[int, IntegrationError], None] | None = None,
) -> tuple[T, int]:
    started = monotonic()
    rng = random_source or random.Random()
    for attempt in range(1, policy.maximum_attempts + 1):
        try:
            return await operation(), attempt - 1
        except asyncio.CancelledError:
            raise
        except IntegrationError as exc:
            elapsed = monotonic() - started
            if not exc.retryable or attempt >= policy.maximum_attempts:
                raise
            delay = exc.retry_after_seconds
            if delay is None:
                delay = min(policy.maximum_delay_seconds, policy.base_delay_seconds * 2 ** (attempt - 1))
                delay *= 1 + rng.uniform(-policy.jitter_ratio, policy.jitter_ratio)
            if elapsed + delay > policy.maximum_elapsed_seconds:
                raise
            if on_retry:
                on_retry(attempt, exc)
            await asyncio.sleep(max(0.0, delay))
    raise AssertionError("bounded retry loop exhausted")
