from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from packages.streaming.adapters import ADAPTERS, get_adapter
from packages.streaming.contracts import MessagingBacklog, MessagingSystem, ResourceKind, SqsFacet
from packages.streaming.identity import canonical_messaging_id

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def observation(system="sqs", kind="queue", native="arn:example:one"):
    return {
        "tenant_id": "tenant-a",
        "environment": "prod",
        "provider_account_scope": "123456789012",
        "cloud_region_or_location": "us-east-1",
        "namespace": "payments",
        "resource_kind": kind,
        "provider_resource_id": native,
        "name": "display-name",
        "observed_at": NOW,
        "confidence": 0.8,
        "source_coverage": 0.7,
        "backlog_messages": 0,
    }


def test_all_systems_have_explicit_registry_entries():
    assert set(ADAPTERS) == {s.value for s in MessagingSystem if s != MessagingSystem.UNKNOWN}
    with pytest.raises(ValueError, match="unsupported messaging system"):
        get_adapter("caller.module.BadAdapter")


def test_identity_is_scope_and_kind_sensitive_not_display_name_based():
    args = dict(
        tenant_id="t",
        environment="p",
        messaging_system="sqs",
        provider_account_scope="a",
        region_or_location="r",
        namespace="n",
        resource_kind="queue",
        provider_resource_id="arn:q",
    )
    value = canonical_messaging_id(**args)
    assert value == canonical_messaging_id(**args)
    assert value != canonical_messaging_id(**(args | {"resource_kind": "stream"}))
    assert value != canonical_messaging_id(**(args | {"provider_account_scope": "other"}))


def test_sqs_zero_is_preserved_and_missing_is_null_with_approximate_semantics():
    backlog = get_adapter("sqs").backlog(observation())
    assert backlog.backlog_messages == 0
    assert backlog.backlog_age_seconds is None
    assert backlog.measurement_method == "provider_approximate"
    assert backlog.model_dump()["backlog_age_seconds"] is None


def test_queue_cannot_be_normalized_by_kinesis_and_provider_facets_are_strict():
    with pytest.raises(ValueError, match="not valid"):
        get_adapter("kinesis").resource(observation(kind="queue"))
    with pytest.raises(ValidationError):
        SqsFacet(fifo=True, policy_document={"secret": True})


def test_sqs_unsupported_kafka_concepts_are_explicit():
    capabilities = get_adapter("sqs").capabilities()
    assert capabilities.offsets == "unsupported"
    assert capabilities.consumer_groups == "unsupported"
    assert capabilities.partitions == "unsupported"
    assert capabilities.backlog_count == "available"


def test_contract_rejects_extra_fields():
    with pytest.raises(ValidationError):
        MessagingBacklog(
            id="x",
            tenant_id="t",
            environment="e",
            messaging_system="sqs",
            resource_id="r",
            observed_at=NOW,
            measurement_method="provider_measured",
            message_payload="forbidden",
        )


def test_provider_ids_do_not_collide_for_same_native_id():
    sqs = get_adapter("sqs").canonical_id(observation())
    kinesis = get_adapter("kinesis").canonical_id(observation(kind="stream"))
    assert sqs != kinesis
