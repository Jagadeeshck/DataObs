from __future__ import annotations

import asyncio
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from integrations.gcp.authentication import parse_authentication
from integrations.gcp.clients import ReadOnlyClient
from integrations.gcp.configuration import parse_gcp_configuration
from integrations.gcp.errors import GoogleCloudCollectorError
from integrations.gcp.evidence import delivery_type, metric, subscription, topic
from integrations.gcp.monitoring import ALLOWED_METRICS, REGIONAL_BACKLOG_METRICS, validate_metric
from integrations.gcp.provider import GoogleCloudMessagingProvider
from packages.collectors.sdk import Capability, EvidenceState, IntegrationContext
from packages.streaming.adapters.provider import require_observation_envelope
from packages.streaming.adapters.pubsub import PubSubAdapter
from services.collection_manager.cli import build_registry


def configuration(**overrides):
    value = {
        "services": ["pubsub"],
        "authentication": {"type": "application_default"},
        "projects": [{"project_id": "example-prod"}],
        "pubsub": {},
        "monitoring": {},
        "limits": {},
    }
    value.update(overrides)
    return value


@pytest.fixture()
def context():
    return IntegrationContext(
        "tenant-a",
        "gcp-one",
        "run-one",
        datetime.now(timezone.utc) + timedelta(minutes=5),
        attributes={"environment": "prod"},
    )


def test_registration_identity_and_capabilities():
    provider = build_registry().create("gcp")
    assert isinstance(provider, GoogleCloudMessagingProvider)
    assert (provider.provider_type, provider.provider_version) == ("gcp", "1")
    assert {
        Capability.RESOURCE_DISCOVERY,
        Capability.METRIC_COLLECTION,
        Capability.INCREMENTAL_COLLECTION,
    } <= provider.capabilities().supported
    assert Capability.EVENT_DRIVEN_COLLECTION in provider.capabilities().unsupported
    assert build_registry().create("bigquery").provider_type == "bigquery"


def test_core_registry_import_does_not_require_google_clients():
    script = """
import builtins
real_import = builtins.__import__
def guarded(name, *args, **kwargs):
    if name == 'google.cloud' or name.startswith('google.cloud.'):
        raise AssertionError('eager Google client import')
    return real_import(name, *args, **kwargs)
builtins.__import__ = guarded
from services.collection_manager.cli import build_registry
assert build_registry().create('gcp').provider_type == 'gcp'
"""
    result = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_configuration_is_closed_explicit_and_bounded():
    parsed = parse_gcp_configuration(configuration())
    assert parsed.services == {"pubsub"} and parsed.projects[0].project_id == "example-prod"
    for invalid in (
        configuration(unknown=True),
        configuration(projects=[]),
        configuration(projects=[{"project_id": "INVALID"}]),
        configuration(services=["pubsub", "bigquery"]),
    ):
        with pytest.raises(GoogleCloudCollectorError):
            parse_gcp_configuration(invalid)


def test_authentication_modes_and_legacy_key_boundary():
    assert parse_authentication({"type": "application_default"}).type == "application_default"
    assert (
        parse_authentication({"type": "workload_identity", "credential_config_ref": "env:GCP_WIF_CONFIG"}).type
        == "workload_identity"
    )
    impersonation = parse_authentication(
        {
            "type": "service_account_impersonation",
            "target_principal": "collector@example-prod.iam.gserviceaccount.com",
            "delegates": [],
            "lifetime_seconds": 900,
        }
    )
    assert impersonation.lifetime_seconds == 900
    with pytest.raises(GoogleCloudCollectorError):
        parse_authentication({"type": "service_account_key_legacy", "credentials_ref": "env:GCP_KEY"})
    assert (
        parse_authentication(
            {"type": "service_account_key_legacy", "credentials_ref": "env:GCP_KEY"}, allow_legacy=True
        ).credentials_ref
        == "env:GCP_KEY"
    )


def test_workload_identity_rejects_inline_and_executable_sources():
    with pytest.raises(GoogleCloudCollectorError):
        parse_authentication({"type": "workload_identity", "credential_config_ref": '{"type":"external_account"}'})


def test_read_only_client_blocks_all_message_and_mutation_operations():
    raw = SimpleNamespace(list_topics=lambda **_: [])
    client = ReadOnlyClient(raw, frozenset({"list_topics"}))
    assert client.invoke("list_topics") == []
    for operation in (
        "publish",
        "pull",
        "streaming_pull",
        "acknowledge",
        "modify_ack_deadline",
        "seek",
        "create_topic",
        "update_topic",
        "delete_topic",
        "create_subscription",
        "update_subscription",
        "delete_subscription",
        "create_snapshot",
        "delete_snapshot",
    ):
        with pytest.raises(GoogleCloudCollectorError):
            client.invoke(operation)


def test_topic_evidence_redacts_cmek_schema_and_transforms(context):
    item = SimpleNamespace(
        name="projects/example-prod/topics/orders",
        message_retention_duration=timedelta(days=7),
        kms_key_name="projects/p/locations/l/keyRings/r/cryptoKeys/secret",
        schema_settings=SimpleNamespace(schema="projects/p/schemas/private"),
        message_transforms=[{"javascript_udf": "secret"}],
        ingestion_data_source_settings=object(),
    )
    result = topic(context, "example-prod", item)
    evidence = result.source_evidence
    assert evidence["cmek_enabled"] and evidence["schema_attached"] and evidence["message_transform_count"] == 1
    serialized = repr(evidence)
    assert "cryptoKeys" not in serialized and "javascript_udf" not in serialized and "schemas/private" not in serialized


def test_subscription_privacy_delivery_and_declared_semantics(context):
    item = SimpleNamespace(
        name="projects/example-prod/subscriptions/orders",
        topic="projects/example-prod/topics/orders",
        ack_deadline_seconds=30,
        retain_acked_messages=True,
        message_retention_duration=timedelta(days=2),
        expiration_policy=SimpleNamespace(ttl=timedelta(days=31)),
        enable_exactly_once_delivery=True,
        enable_message_ordering=True,
        push_config=SimpleNamespace(push_endpoint="https://secret.invalid", oidc_token="principal"),
        bigquery_config=None,
        cloud_storage_config=None,
        retry_policy=SimpleNamespace(minimum_backoff=timedelta(seconds=10), maximum_backoff=timedelta(seconds=60)),
        dead_letter_policy=None,
        filter='attributes.private="secret"',
    )
    resource, dlq = subscription(context, "example-prod", item, frozenset())
    evidence = resource.source_evidence
    assert delivery_type(item) == "push" and evidence["delivery_type"] == "push"
    assert evidence["exactly_once_delivery"] is True and evidence["ordering_enabled"] is True
    assert evidence["filter_present"] and len(evidence["filter_fingerprint"]) == 64 and dlq is None
    serialized = repr(evidence)
    assert (
        "secret.invalid" not in serialized and "principal" not in serialized and "attributes.private" not in serialized
    )


def test_dead_letter_topic_only_emitted_when_visible(context):
    dlq_id = "projects/example-prod/topics/orders-dlq"
    item = SimpleNamespace(
        name="projects/example-prod/subscriptions/orders",
        topic="projects/example-prod/topics/orders",
        dead_letter_policy=SimpleNamespace(dead_letter_topic=dlq_id, max_delivery_attempts=10),
        filter="",
    )
    _, hidden = subscription(context, "example-prod", item, frozenset())
    resource, visible = subscription(context, "example-prod", item, frozenset({dlq_id}))
    assert hidden is None and visible is not None
    assert visible.source_evidence["source_subscription_resource_id"] == resource.native_resource_id


def test_team1_envelope_and_adapter_identity_are_replay_stable(context):
    observation = topic(context, "example-prod", SimpleNamespace(name="projects/example-prod/topics/orders"))
    envelope = dict(observation.source_evidence)
    require_observation_envelope(envelope)
    first = PubSubAdapter().resource(envelope)
    second = PubSubAdapter().resource(envelope)
    assert first.id == second.id and first.provider == "gcp" and first.messaging_system == "google_pubsub"


def test_metric_allowlist_missing_zero_and_type_semantics(context):
    resource = topic(context, "example-prod", SimpleNamespace(name="projects/example-prod/topics/orders"))
    metric_name = next(iter(REGIONAL_BACKLOG_METRICS))
    assert validate_metric(metric_name) in ALLOWED_METRICS
    zero = metric(resource, metric_name, 0.0, "GAUGE", 60, region="us-central1")
    missing = metric(resource, metric_name, None, "GAUGE", 60, region="us-central1")
    delta = metric(resource, "pubsub.googleapis.com/topic/send_request_count", 4.0, "DELTA", 60)
    assert zero.state == EvidenceState.MEASURED and zero.value == 0
    assert missing.state == EvidenceState.MISSING and missing.value is None
    assert delta.aggregation == "delta_window" and delta.period_seconds == 60
    with pytest.raises(ValueError):
        validate_metric("pubsub.googleapis.com/subscription/deprecated_metric")


def test_dependency_unavailable_is_partial_failure(context):
    class MissingFactory:
        def create(self, _cfg):
            raise GoogleCloudCollectorError("dependency_unavailable", "dependencies")

    provider = GoogleCloudMessagingProvider(MissingFactory())

    async def exercise():
        assert (await provider.validate_configuration(context, configuration())).valid
        request = SimpleNamespace(capabilities=frozenset({Capability.RESOURCE_DISCOVERY}))
        return [item async for item in provider.collect(context, request)]

    results = asyncio.run(exercise())
    assert results[0].error_code == "dependency_unavailable"


def test_provider_collects_topics_subscriptions_with_trusted_scope(context):
    topic_item = SimpleNamespace(name="projects/example-prod/topics/orders")
    subscription_item = SimpleNamespace(
        name="projects/example-prod/subscriptions/orders",
        topic=topic_item.name,
        dead_letter_policy=None,
        filter="",
    )

    class Client:
        def __init__(self, items):
            self.items = items

        def invoke(self, operation, **_kwargs):
            assert operation in {"list_topics", "list_subscriptions"}
            return self.items

    class Factory:
        def create(self, _cfg):
            return Client([topic_item]), Client([subscription_item]), Client([])

    provider = GoogleCloudMessagingProvider(Factory())

    async def exercise():
        assert (await provider.validate_configuration(context, configuration())).valid
        request = SimpleNamespace(
            capabilities=frozenset({Capability.RESOURCE_DISCOVERY, Capability.METADATA_COLLECTION})
        )
        return [item async for item in provider.collect(context, request)]

    results = asyncio.run(exercise())
    assert [item.resource_type for item in results] == ["topic", "subscription"]
    assert all(item.source_evidence["tenant_id"] == "tenant-a" for item in results)
    assert all(item.source_evidence["environment"] == "prod" for item in results)


def test_no_payload_fields_exist_in_provider_evidence(context):
    observation = topic(context, "example-prod", SimpleNamespace(name="projects/example-prod/topics/orders"))
    evidence = observation.source_evidence
    assert evidence["raw_message_payloads_read"] is False
    assert not ({"message.data", "message.attributes", "ordering_key", "ack_id"} & set(evidence))
