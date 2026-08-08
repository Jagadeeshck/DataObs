import pytest

from integrations.database import DatabaseIdentity, FixedStatementRegistry, Statement, validate_identifier
from integrations.database.schema import structural_fingerprint


def test_identity_isolated_and_deterministic():
    a = DatabaseIdentity("tenant", "prod", "postgres", "one", "instance", "db")
    assert a.canonical_id("public", "orders") == a.canonical_id("public", "orders")
    assert a.canonical_id("public", "orders") != DatabaseIdentity(
        "tenant", "test", "postgres", "one", "instance", "db"
    ).canonical_id("public", "orders")
    assert a.canonical_id() != DatabaseIdentity("tenant", "prod", "postgres", "two", "instance", "db").canonical_id()


def test_identifiers_and_mutation_rejected():
    assert validate_identifier("safe_name$1") == "safe_name$1"
    with pytest.raises(ValueError):
        validate_identifier("orders; DROP TABLE x")
    for sql in ("DELETE FROM x", "WITH x AS (SELECT 1) UPDATE y SET a=1", "SET ROLE admin"):
        with pytest.raises(ValueError):
            FixedStatementRegistry((Statement("bad", sql, 1),))
    registry = FixedStatementRegistry((Statement("health", "SELECT 1", 1),))
    with pytest.raises(ValueError):
        registry.get("configuration-controlled")


def test_structural_evidence_is_order_stable_and_private_text_excluded():
    left = [{"column": "a", "type": "int", "default": "secret", "observed_at": "now"}, {"column": "b", "type": "text"}]
    right = [
        {"column": "b", "type": "text"},
        {"column": "a", "type": "int", "default": "different", "observed_at": "later"},
    ]
    assert structural_fingerprint(left) == structural_fingerprint(right)
