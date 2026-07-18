import pytest

from packages.domain_model import Asset, Source, Tenant, deterministic_id


def test_deterministic_ids_are_stable():
    assert deterministic_id("asset", ["Tenant A", "Prod", "db.table"]) == deterministic_id(
        "asset", ["tenant-a", "prod", "db.table"]
    )


def test_json_schema_and_schema_version():
    schema = Tenant.model_json_schema()
    assert "schema_version" in schema["properties"]
    t = Tenant.build("acme", "Acme", "acme")
    assert t.schema_version == "v1"


def test_source_rejects_secret_endpoint_metadata():
    with pytest.raises(ValueError):
        Source.build("t", "dev", "pg", "postgres", "postgres", endpoint={"password": "secret"})


def test_legacy_pillar_serializes_canonical():
    a = Asset.build("t", "dev", "db", "db.public.orders", "table", "source-1", pillar="full_stack")
    assert a.model_dump(mode="json")["pillar"] == "platform"
