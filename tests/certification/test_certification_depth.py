"""Reject regression to presence-only provider certification."""

import ast
from pathlib import Path

SUITES = ("migrations", "postgres", "kafka", "openlineage", "product_queries", "incidents", "otel", "security")
LIVE_TOKENS = ("live_stack", "ApiClient", "ElasticsearchClient", "PostgresClient", "KafkaClient", "request(", "urlopen")


def test_every_required_suite_contains_live_and_dataobs_assertions():
    for suite in SUITES:
        path = Path(__file__).with_name(f"test_{suite}.py")
        source = path.read_text()
        ast.parse(source)
        assert "assert" in source, f"{path} contains no assertions"
        assert any(token in source for token in LIVE_TOKENS), f"{path} has no live assertion"
        assert any(
            token in source for token in ("live_stack", "api", "es", "ElasticsearchClient")
        ), f"{path} has no DataObs assertion"
        assert "harness_is_present" not in source, f"{path} regressed to presence-only certification"
