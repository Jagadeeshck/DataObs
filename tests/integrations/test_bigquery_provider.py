from datetime import datetime, timedelta, timezone

import pytest

from integrations.bigquery.authentication import parse_authentication
from integrations.bigquery.clients import ReadOnlyClient
from integrations.bigquery.configuration import parse_configuration
from integrations.bigquery.identifiers import dataset_id, location_id, project_id
from integrations.bigquery.pagination import Page, collect_pages
from integrations.bigquery.provider import BigQueryWarehouseProvider
from integrations.bigquery.sql import TEMPLATES
from packages.collectors.sdk import Capability, ProviderRegistry


def config():
    return {
        "authentication": {"type": "application_default"},
        "projects": [{"project_id": "synthetic-project", "locations": ["EU", "europe-west2"]}],
        "query_execution": {"billing_project": "synthetic-billing"},
    }


def test_registry_identity_and_capabilities():
    r = ProviderRegistry()
    r.register(BigQueryWarehouseProvider)
    assert r.provider_types() == ("bigquery",)
    assert BigQueryWarehouseProvider.provider_version == "1"
    assert Capability.QUERY_HISTORY in r.create("bigquery").capabilities().supported
    assert Capability.COST_COLLECTION in r.create("bigquery").capabilities().unsupported
    with pytest.raises(ValueError):
        r.register(BigQueryWarehouseProvider)


def test_closed_bounded_configuration():
    c = parse_configuration(config())
    assert c.projects[0].locations == ("EU", "europe-west2")
    for bad in (
        {**config(), "endpoint": "https://evil"},
        {**config(), "projects": []},
        {**config(), "projects": [{"project_id": "synthetic-project", "locations": []}]},
    ):
        with pytest.raises(Exception):
            parse_configuration(bad)


@pytest.mark.parametrize(
    "fn,bad",
    [
        (project_id, "abc`; SELECT 1--"),
        (project_id, "a.bbbbb"),
        (dataset_id, "x/y"),
        (dataset_id, "x;DROP"),
        (location_id, "EU.foo"),
        (location_id, "EU --"),
        (location_id, "europe/west"),
    ],
)
def test_identifier_injection_rejected(fn, bad):
    with pytest.raises(Exception):
        fn(bad)


def test_authentication_boundaries():
    assert parse_authentication({"type": "application_default"}).type == "application_default"
    assert (
        parse_authentication(
            {"type": "workload_identity", "credential_config_ref": "env:GOOGLE_APPLICATION_CREDENTIALS"}
        ).type
        == "workload_identity"
    )
    assert (
        parse_authentication(
            {
                "type": "service_account_impersonation",
                "target_principal": "dataobs@synthetic-project.iam.gserviceaccount.com",
                "lifetime_seconds": 1800,
            }
        ).lifetime_seconds
        == 1800
    )
    for raw in (
        {"type": "workload_identity", "credential_config_ref": "/tmp/a"},
        {"type": "service_account_key_legacy", "credentials_ref": "env:KEY"},
        {"type": "api_key", "value": "x"},
        {"type": "application_default", "scopes": ["evil"]},
    ):
        with pytest.raises(Exception):
            parse_authentication(raw)


def test_fixed_sql_is_private_bounded_and_regional():
    forbidden = (
        "SELECT *",
        "USER_EMAIL",
        "PRINCIPAL_SUBJECT",
        "SESSION_INFO",
        " LABELS",
        " QUERY,",
        "INSERT ",
        "DELETE ",
        "UPDATE ",
        "CREATE ",
    )
    for factory in TEMPLATES:
        q = factory("synthetic-project", "EU", 100)
        upper = q.sql.upper()
        assert not any(x in upper for x in forbidden)
        assert "REGION-EU.INFORMATION_SCHEMA" in upper
        assert "@START_TIME" in upper and "@END_TIME" in upper and "ORDER BY" in upper and "LIMIT 100" in upper


def test_pagination_bounds_dedup_and_loop():
    pages = {None: Page(({"id": "b"},), "a"), "a": Page(({"id": "a"}, {"id": "b"}), None)}
    assert [
        x["id"] for x in collect_pages(lambda t: pages[t], lambda x: x["id"], maximum_pages=3, maximum_results=5)
    ] == ["a", "b"]
    with pytest.raises(Exception):
        collect_pages(lambda _: Page((), "same"), str, maximum_pages=3, maximum_results=3)


def test_read_allowlist_rejects_rows_mutations_and_arbitrary_sql():
    class Raw:
        pass

    c = ReadOnlyClient(Raw())
    for operation in ("list_rows", "delete_table", "cancel_job", "query"):
        with pytest.raises(Exception):
            c.invoke(operation)


def test_optional_dependency_is_lazy():
    assert BigQueryWarehouseProvider().provider_type == "bigquery"
