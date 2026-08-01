import asyncio
import json
import tarfile

import pytest

from scripts.operations.collect_support_bundle import collect
from src.platform_operations.attributes import validate_metric_attributes
from src.platform_operations.health import CachedHealthCheck, Criticality, HealthState
from src.platform_operations.slo import evaluate_error_budget


def test_attribute_policy():
    validate_metric_attributes({"http.route": "/api/v1/assets/{asset_id}", "http.request.method": "GET"})
    for key in ("url.path", "request_id", "tenant_id", "exception.message", "sql"):
        with pytest.raises(ValueError):
            validate_metric_attributes({key: "secret"})


def test_missing_slo_evidence_is_insufficient():
    result = evaluate_error_budget(
        good_events=None, total_events=None, objective=0.99, window_seconds=60, data_completeness=0
    )
    assert result.evaluation_state == "insufficient_data" and result.achieved_ratio is None


def test_health_cache_and_timeout():
    calls = 0

    async def scenario():
        nonlocal calls

        async def probe():
            nonlocal calls
            calls += 1
            return HealthState.HEALTHY, "ok"

        check = CachedHealthCheck(ttl_seconds=10, timeout_seconds=0.1)
        await check.run("repository", Criticality.READINESS, probe)
        await check.run("repository", Criticality.READINESS, probe)

    asyncio.run(scenario())
    assert calls == 1


def test_support_bundle_redacts_and_is_allowlisted(tmp_path):
    source = tmp_path / "in"
    source.mkdir()
    (source / "version.json").write_text(json.dumps({"version": "1", "token": "secret"}))
    (source / "unknown.json").write_text("{}")
    output = tmp_path / "bundle.tgz"
    inventory = collect(source, output, timestamp=123)
    assert [x["path"] for x in inventory] == ["version.json"]
    with tarfile.open(output) as tar:
        assert b"secret" not in tar.extractfile("version.json").read()
        assert json.load(tar.extractfile("manifest.json"))["created_at_epoch"] == 123
