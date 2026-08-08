import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace as N

import pytest
import yaml

from integrations.azure.authentication import parse_authentication
from integrations.azure.clients import ALLOWED_OPERATIONS, ReadOnlyAzureClients
from integrations.azure.configuration import parse_configuration
from integrations.azure.identifiers import (
    filesystem,
    path_prefix,
    resource_group,
    service_name,
    storage_account,
    synapse_endpoint,
)
from integrations.azure.provider import AzureDataPlatformProvider
from packages.collectors.sdk import Capability, CollectionRequest, IntegrationContext, ProviderRegistry


def raw():
    return yaml.safe_load(open("config/integrations/azure-data-platform.example.yaml"))["provider"]


class Factory:
    def __init__(self, ops):
        self.client = ReadOnlyAzureClients(ops)

    def create(self, cfg):
        return self.client

    def close(self, c):
        pass

    def versions(self):
        return {}


def operations():
    now = datetime.now(timezone.utc)
    return {
        "subscription_get": lambda: N(subscription_id="11111111-1111-1111-1111-111111111111"),
        "factory_get": lambda *a: N(
            location="eastus", provisioning_state="Succeeded", identity=N(), repo_configuration=N()
        ),
        "pipeline_list": lambda *a: [
            N(
                name="safe-pipeline",
                activities=[N(depends_on=[], policy={"retry": 1})],
                parameters={"secret": "omitted"},
                variables={"x": "omitted"},
                concurrency=1,
            )
        ],
        "trigger_list": lambda *a: [N(name="daily", runtime_state="Started", pipelines=[1])],
        "adf_pipeline_runs_query": lambda *a: [
            N(
                run_id="r1",
                pipeline_name="safe-pipeline",
                status="Succeeded",
                run_start=now - timedelta(seconds=1),
                run_end=now,
                last_updated=now,
                run_dimensions={},
            )
        ],
        "adf_activity_runs_query": lambda *a: [
            N(
                activity_run_id="a1",
                activity_name="copy",
                activity_type="Copy",
                status="Failed",
                activity_run_start=now - timedelta(seconds=1),
                activity_run_end=now,
                input={"secret": 1},
                output={"secret": 2},
                error={"message": "secret"},
            )
        ],
        "workspace_get": lambda *a: N(location="eastus", provisioning_state="Succeeded", identity=N()),
        "sql_pool_list": lambda *a: [N(name="pool", status="Online", sku=N(name="DW100c", capacity=100))],
        "spark_pool_list": lambda *a: [
            N(
                name="spark",
                provisioning_state="Succeeded",
                spark_version="3.4",
                auto_scale=N(enabled=True, min_node_count=3, max_node_count=10),
                auto_pause=N(enabled=True, delay_in_minutes=15),
            )
        ],
        "synapse_pipeline_list": lambda *a: [N(name="synpipe", activities=[], parameters={"x": "secret"})],
        "synapse_pipeline_runs_query": lambda *a: [],
        "synapse_activity_runs_query": lambda *a: [],
        "storage_account_get": lambda *a: N(
            location="eastus", kind="StorageV2", is_hns_enabled=True, sku=N(name="Standard_LRS")
        ),
        "filesystem_list": lambda *a: [N(name="curated", metadata={"x": "not emitted"})],
        "path_list": lambda *a: [
            N(name="datasets/customer/a.parquet", is_directory=False, content_length=9, last_modified=now)
        ],
    }


def test_registration_capabilities_and_dependency_boundary():
    r = ProviderRegistry()
    r.register(AzureDataPlatformProvider)
    assert r.provider_types() == ("azure",) and r.create("azure").provider_version == "1"
    assert Capability.INCREMENTAL_COLLECTION in r.create("azure").capabilities().supported
    assert Capability.QUERY_HISTORY in r.create("azure").capabilities().unsupported
    with pytest.raises(ValueError):
        r.register(AzureDataPlatformProvider)


def test_closed_explicit_configuration_and_authentication():
    cfg = parse_configuration(raw())
    assert cfg.subscription_id.startswith("1111") and cfg.authentication.type == "managed_identity"
    for auth in (
        {"type": "workload_identity", "client_id_ref": "env:CLIENT_ID", "token_file_ref": "env:TOKEN_FILE"},
        {"type": "service_principal_secret", "client_id_ref": "env:CLIENT_ID", "client_secret_ref": "env:SECRET"},
    ):
        assert parse_authentication(auth, cfg.tenant_id).type == auth["type"]
    for bad in (
        {"type": "interactive_browser"},
        {"type": "azure_cli"},
        {"type": "service_principal_secret", "client_id_ref": "inline", "client_secret_ref": "secret"},
    ):
        with pytest.raises(Exception):
            parse_authentication(bad, cfg.tenant_id)
    x = raw()
    x["endpoint"] = "http://evil"
    with pytest.raises(Exception):
        parse_configuration(x)


def test_identifier_and_endpoint_safety():
    assert synapse_endpoint("safe-workspace") == "https://safe-workspace.dev.azuresynapse.net"
    for fn, values in (
        (resource_group, ["..", "x/control\n"]),
        (service_name, ["https://evil", "bad/name"]),
        (storage_account, ["UPPER", "a"]),
        (filesystem, ["bad--name", "https://x"]),
        (path_prefix, ["../secret", "https://evil/x", "/override", "x?sig=secret"]),
    ):
        for value in values:
            with pytest.raises(ValueError):
                fn(value)


def test_read_allowlist_prohibits_mutations_and_content_reads():
    client = ReadOnlyAzureClients({})
    assert "factory_get" in ALLOWED_OPERATIONS
    for operation in (
        "create_run",
        "cancel",
        "pool_update",
        "list_keys",
        "generate_sas",
        "download_file",
        "upload_data",
        "set_access_control_recursive",
        "send_request",
    ):
        with pytest.raises(Exception):
            client.invoke(operation)


def test_safe_collection_and_aggregate_prefix():
    asyncio.run(_safe_collection_and_aggregate_prefix())


async def _safe_collection_and_aggregate_prefix():
    cfgraw = raw()
    cfgraw["adls_gen2"][0]["prefix_observations"]["enabled"] = True
    provider = AzureDataPlatformProvider(Factory(operations()))
    ctx = IntegrationContext(
        "tenant-a",
        "integration-a",
        "run-a",
        datetime.now(timezone.utc) + timedelta(seconds=30),
        attributes={"environment": "test"},
    )
    assert (await provider.validate_configuration(ctx, cfgraw)).valid
    request = CollectionRequest(frozenset({Capability.METADATA_COLLECTION, Capability.INCREMENTAL_COLLECTION}))
    items = [x async for x in provider.collect(ctx, request)]
    evidence = [dict(x.source_evidence) for x in items if hasattr(x, "source_evidence")]
    families = {x["evidence_family"] for x in evidence}
    assert {
        "adf.factory",
        "adf.pipeline",
        "adf.trigger",
        "adf.pipeline_run",
        "adf.activity_run",
        "synapse.workspace",
        "synapse.sql_pool",
        "synapse.spark_pool",
        "synapse.pipeline",
        "adls.account",
        "adls.filesystem",
        "adls.prefix_observation",
    } <= families
    rendered = repr(evidence).lower()
    assert (
        "secret" not in rendered
        and "a.parquet" not in rendered
        and "input" not in rendered
        and "output" not in rendered
    )
    prefix = next(x for x in evidence if x["evidence_family"] == "adls.prefix_observation")
    assert (
        prefix["file_count_observed"] == 1 and prefix["total_content_length"] == 9 and not prefix["path_names_emitted"]
    )
    assert not any(
        x.provider != "azure" or x.account != cfgraw["subscription_id"] for x in items if hasattr(x, "provider")
    )
