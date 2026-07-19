from datetime import datetime, timedelta, timezone

from services.kafka_observer.leases import DurableLeases, MemoryLeaseRepository
from services.kafka_observer.offsets import lag_velocity


def test_lease_excludes_another_owner_and_can_be_released():
    leases = DurableLeases(MemoryLeaseRepository())
    assert leases.acquire("inventory", "one", 30)
    assert not leases.acquire("inventory", "two", 30)
    leases.release("inventory", "one")
    assert leases.acquire("inventory", "two", 30)


def test_lag_velocity_uses_robust_median_slope():
    now = datetime.now(timezone.utc)
    samples = [
        (now, 0),
        (now + timedelta(seconds=10), 10),
        (now + timedelta(seconds=20), 1_000),  # isolated spike
        (now + timedelta(seconds=30), 30),
    ]
    result = lag_velocity(samples)
    assert result["method"] == "median_pairwise_slope"
    assert result["messages_per_second"] == 1.0
