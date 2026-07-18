from __future__ import annotations

import os
from datetime import datetime, timezone

import pytest

from integrations.databases.postgres.connector import PostgresConnector
from integrations.databases.postgres.models import PostgresConnectionConfig
from packages.agent_sdk.models import (
    ConnectorIdentity,
    DiscoveryRequest,
    FreshnessRequest,
    ProfileRequest,
    ResultMetadata,
)
from services.collection_manager import CollectionManagerService
from services.collection_manager.leases import claim_task
from services.collection_manager.repository import ConflictError


def _meta(op="discover"):
    return ResultMetadata(
        "tenant-it",
        "test",
        "pg-it",
        ConnectorIdentity("postgres", "0.2.0", "postgres"),
        f"exec-{op}",
        f"task-{op}",
        datetime.now(timezone.utc),
        None,
        "postgres",
        "*",
    )


def _config():
    return PostgresConnectionConfig(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB", "dataobs_demo"),
        username=os.getenv("POSTGRES_USER", "dataobs_metadata"),
        password_ref="env://POSTGRES_PASSWORD",
        sslmode=os.getenv("POSTGRES_SSLMODE", "prefer"),
    )


pytestmark = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION_TESTS") != "1", reason="container-backed PostgreSQL/Elasticsearch tests are opt-in"
)


def test_real_postgres_connection_discovery_freshness_and_profile():
    connector = PostgresConnector(
        _config(),
        allow_schemas=["public", "analytics"],
        scanner_id="scanner-it",
        task_context={"tenant_id": "tenant-it", "integration_id": "pg-it", "task_id": "task-it"},
    )
    try:
        assert connector.test_connection().ok
        discovered = connector.discover(DiscoveryRequest(_meta())).assets
        assert any(a["table"] == "orders" for a in discovered)
        fresh = connector.freshness(
            FreshnessRequest(_meta("freshness"), {"table": "public.orders", "timestamp_column": "updated_ts"})
        )
        assert fresh.watermarks["strategy"] == "max_timestamp_column"
        profile = connector.profile(
            ProfileRequest(
                _meta("profile"),
                {
                    "enable_aggregate_profiling": True,
                    "table": "public.orders",
                    "columns": [{"name": "amount"}, {"name": "status"}, {"name": "password_hint"}],
                },
            )
        )
        assert profile.raw_rows_persisted is False
        assert "amount" in profile.metrics["columns"]
        assert profile.metrics["denied_columns"]
        cp = connector.checkpoint()
        assert cp.tenant_id == "tenant-it" and cp.integration_id == "pg-it"
    finally:
        connector.close()


def test_task_claim_exclusivity_memory_matches_es_contract():
    svc = CollectionManagerService()
    scanner = svc.register("scanners", "tenant-it", {"scanner_identity": "scanner-it"}, "scanner")
    policy = svc.create_policy("tenant-it", {"source_id": "source-it", "operation": "discover", "enabled": True})
    task = svc.tasks_for_scanner("tenant-it", scanner["id"])[0]
    first = claim_task(svc.repo, "tenant-it", scanner["id"], task["id"])
    assert first["status"] == "leased"
    with pytest.raises(ConflictError):
        claim_task(svc.repo, "tenant-it", "other-scanner", task["id"])
    assert policy["tenant_id"] == "tenant-it"
