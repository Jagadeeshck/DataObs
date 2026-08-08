from __future__ import annotations

from dataclasses import dataclass

import pytest

from packages.elastic_store.manifest import migrations
from packages.elastic_store.registry import apply, status
from scripts.validate_capability_ledger import validate


@dataclass
class _Indices:
    docs: list[dict]

    def exists(self, *, index: str) -> bool:
        return index == "dataobs-system-migrations-v1"


class _ES:
    def __init__(self, docs: list[dict]):
        self.docs = docs
        self.indices = _Indices(docs)

    def search(self, **_kwargs):
        return {"hits": {"hits": [{"_source": doc} for doc in self.docs]}}


def test_reconciliation_is_forward_only_after_released_chain():
    chain = migrations()
    assert [migration.migration_id for migration in chain[-4:]] == [
        "0026_stream_anomaly_retention_intelligence",
        "0027_platform_environment_tenant_multicluster_lifecycle",
        "0028_pathway_investigation_history",
        "0029_team2_data_intelligence_reconciliation",
    ]
    resources = chain[-1].operations
    assert "dataobs-lineage-runtime-state-v1" in resources["mutable_indices"]
    assert "dataobs-data-contract-runtime-state-v1" in resources["mutable_indices"]
    assert resources["data_stream_contracts"]["logs-dataobs.data-contract-version-*"]["retention"] == "3650d"


@pytest.mark.parametrize(
    ("migration_id", "historical_name"),
    [
        ("0026_lineage_impact_change_intelligence", "0026_lineage_impact_change_intelligence"),
        (
            "0027_data_contracts_schema_governance",
            "0027_data_contracts_schema_governance",
        ),
    ],
)
def test_doctor_reports_historical_collision(migration_id: str, historical_name: str):
    report = status(
        _ES(
            [
                {
                    "migration_id": migration_id,
                    "migration_name": historical_name,
                    "checksum": "historical-branch-checksum",
                }
            ]
        )
    )
    conflict = report["conflicts"][0]
    assert report["ready"] is False
    assert conflict["state"] == "migration_registry_conflict"
    assert conflict["observed_stored_name"] == historical_name
    assert "Team 0 approval" in conflict["operator_action_required"]


def test_apply_fails_before_resource_mutation_on_collision():
    es = _ES(
        [
            {
                "migration_id": "0026_lineage_impact_change_intelligence",
                "migration_name": "0026_lineage_impact_change_intelligence",
                "checksum": "wrong",
            }
        ]
    )
    with pytest.raises(RuntimeError, match="migration_registry_conflict"):
        apply(es)


def test_quality_route_family_matches_typed_routes():
    # Regression: /quality/* is a ledger family, not a request for a fake wildcard route.
    errors = validate(__import__("scripts.validate_capability_ledger", fromlist=["load"]).load())
    assert "monitoring.data_quality_console_v1: UI route absent: /quality/*" not in errors
