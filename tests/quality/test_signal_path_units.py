from __future__ import annotations

from src.alerting.dispatcher import DispatchResult
from src.quality.checks.in_memory_null_check import InMemoryNullCheck


def test_in_memory_null_check_is_deterministic() -> None:
    check = InMemoryNullCheck()
    config = {"dataset": "orders", "column": "customer_id", "rows": [{"customer_id": None}], "max_null_pct": 0}
    first = check.run(config, None)
    second = check.run(config, None)
    assert first.status == second.status == "FAIL"
    assert first.details == second.details


def test_dispatch_result_does_not_report_empty_or_partial_delivery_as_success() -> None:
    assert not DispatchResult(deduplicated=True, deliveries=()).completely_successful
