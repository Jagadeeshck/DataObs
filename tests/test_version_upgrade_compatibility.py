from dataclasses import dataclass

import pytest

from scripts.release.validate_migration_graph import validate
from src.platform_lifecycle.compatibility import (
    PlatformProfile,
    ReadinessState,
    RollbackState,
    SupportState,
    assess_upgrade,
    change_level,
    classify_rollback,
    classify_version,
    parse_semver,
)
from src.platform_lifecycle.schema_compatibility import compare_openapi, compare_schema


@dataclass
class M:
    migration_id: str
    dependencies: list
    checksum: str = "x"


def test_migration_graph_rejections():
    assert validate([M("0001_a", []), M("0001_a", [])])["state"] == "invalid"
    assert any("duplicate_ordinal" in e for e in validate([M("0001_a", []), M("0001_b", ["0001_a"])])["errors"])
    assert any("unknown_dependency" in e for e in validate([M("0001_a", ["9999_x"])])["errors"])
    assert any("dependency_cycle" in e for e in validate([M("0001_a", ["0002_b"]), M("0002_b", ["0001_a"])])["errors"])
    assert validate([M("0001_a", []), M("0002_b", [])])["state"] == "ambiguous"
    assert any("checksum_mutation" in e for e in validate([M("0001_a", [])], {"0001_a": "old"})["errors"])


def test_semver_and_change_levels():
    assert parse_semver("1.2.3") == (1, 2, 3)
    with pytest.raises(ValueError):
        parse_semver("1.2")
    assert change_level("1.2.2", "1.2.3") == "patch"
    assert change_level("1.2.2", "1.3.0") == "minor"
    assert change_level("1.2.2", "2.0.0") == "major"


def test_platform_versions_are_truthful():
    assert classify_version("elasticsearch", "9.4.2") == SupportState.COMPATIBLE_UNVALIDATED
    assert classify_version("elasticsearch", "8.9.0") == SupportState.INCOMPATIBLE
    assert classify_version("elasticsearch", "10.0.0") == SupportState.UNKNOWN
    assert classify_version("kubernetes", "1.30.2") == SupportState.COMPATIBLE_UNVALIDATED
    assert classify_version("kubernetes", "1.29.9") == SupportState.INCOMPATIBLE
    assert classify_version("kubernetes", "1.31.0") == SupportState.UNKNOWN


def profile(version="0.2.0", es="9.4.2", kube="1.30.0"):
    return PlatformProfile(
        version, "3.17.0", kube, es, "3.13.0", "22.0.0", "dataobs-oidc-v1", "1.0.0", "1.0.0", "1", "0032_x"
    )


def complete_evidence():
    return {
        "migration_graph": "valid",
        "migration_state": "0032_x",
        "configuration": "non_breaking",
        "restore_validated": True,
        "certification_passed": True,
        "migrations": [{"classification": "additive", "application_backward_compatible": True}],
    }


def test_readiness_needs_supported_and_evidence(monkeypatch):
    monkeypatch.setattr("src.platform_lifecycle.compatibility.classify_version", lambda *x: SupportState.SUPPORTED)
    assert assess_upgrade(profile(), profile("0.2.1"), complete_evidence()).state == ReadinessState.READY
    for key, code in [
        ("migration_graph", "MIGRATION_GRAPH_INVALID"),
        ("restore_validated", "RESTORE_UNVALIDATED"),
        ("certification_passed", "CERTIFICATION_EVIDENCE_MISSING"),
    ]:
        evidence = complete_evidence()
        evidence[key] = False
        result = assess_upgrade(profile(), profile("0.2.1"), evidence)
        assert result.state != ReadinessState.READY and code in result.reason_codes
    evidence = complete_evidence()
    evidence.update(backup_required=True, fresh_backup_manifest=False)
    assert "BACKUP_STALE" in assess_upgrade(profile(), profile("0.2.1"), evidence).reason_codes


def test_rollback_classification():
    assert (
        classify_rollback([{"classification": "additive", "application_backward_compatible": True}])
        == RollbackState.SUPPORTED
    )
    assert (
        classify_rollback([{"classification": "additive", "rollback_barrier": True}]) == RollbackState.BLOCKED_MIGRATION
    )
    assert (
        classify_rollback([{"classification": "additive", "application_backward_compatible": False}])
        == RollbackState.APPLICATION_ONLY
    )
    assert classify_rollback([{"classification": "unknown"}]) == RollbackState.UNVALIDATED


def test_schema_compatibility():
    old = {"properties": {"a": {"type": "string", "enum": ["x", "y"]}}}
    assert (
        compare_schema(old, {"properties": {"a": {"type": "string", "enum": ["x", "y"]}, "b": {"type": "string"}}})[
            "classification"
        ]
        == "non_breaking"
    )
    for new, code in [
        ({"properties": {}}, "FIELD_REMOVED"),
        ({"properties": {"a": {"type": "string"}, "b": {"type": "string"}}, "required": ["b"]}, "REQUIRED_FIELD_ADDED"),
        ({"properties": {"a": {"type": "integer"}}}, "TYPE_CHANGED"),
        ({"properties": {"a": {"type": "string", "enum": ["x"]}}}, "ENUM_NARROWED"),
    ]:
        assert any(x["code"] == code for x in compare_schema(old, new)["changes"])


def test_openapi_routes():
    old = {"paths": {"/a": {"get": {}}}}
    assert compare_openapi(old, {"paths": {"/a": {"get": {}}, "/b": {"get": {}}}})["classification"] == "non_breaking"
    assert compare_openapi(old, {"paths": {}})["classification"] == "breaking"
