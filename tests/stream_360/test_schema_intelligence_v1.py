from datetime import datetime, timedelta, timezone

import pytest

from packages.streaming.schema_intelligence import (
    CompatibilityPolicy,
    CompatibilityResult,
    ExposureState,
    SchemaApplicationBinding,
    SchemaIdentity,
    SchemaType,
    evaluate_consumer_exposure,
    evaluate_schema_change,
    fingerprint_schema,
    resolve_kafka_subject_binding,
    temporal_correlation_text,
)


def evaluate(kind, old, new, policy=CompatibilityPolicy.BACKWARD):
    return evaluate_schema_change(kind, policy, old, new, hash_salt="tenant-secret")


def test_scoped_stable_identity_isolates_tenant_environment_and_registry():
    base = SchemaIdentity("tenant-a", "prod", "registry-a", "orders-value")
    identities = {
        base.subject_id,
        SchemaIdentity("tenant-b", "prod", "registry-a", "orders-value").subject_id,
        SchemaIdentity("tenant-a", "dev", "registry-a", "orders-value").subject_id,
        SchemaIdentity("tenant-a", "prod", "registry-b", "orders-value").subject_id,
    }
    assert len(identities) == 4
    assert base.subject_id == SchemaIdentity("tenant-a", "prod", "registry-a", "orders-value").subject_id


def test_avro_structural_rules_are_format_specific_and_field_names_are_hashed():
    old = {"fields": [{"name": "sensitive_customer_name", "type": "long"}]}
    new = {"fields": [{"name": "sensitive_customer_name", "type": "int"}, {"name": "secret_note", "type": "string"}]}
    result = evaluate(SchemaType.AVRO, old, new)
    assert result.result is CompatibilityResult.INCOMPATIBLE
    assert result.change_set.summary.change_categories == (
        "field_added",
        "field_requiredness_changed",
        "field_type_narrowed",
    )
    assert "sensitive_customer_name" not in repr(result)
    assert "secret_note" not in repr(result)


@pytest.mark.parametrize(
    ("new_field", "expected"),
    [
        ({"name": "optional", "type": ["null", "string"], "default": None}, CompatibilityResult.COMPATIBLE),
        ({"name": "required", "type": "string"}, CompatibilityResult.INCOMPATIBLE),
    ],
)
def test_avro_additions_are_conservative_without_authoritative_provider(new_field, expected):
    result = evaluate(SchemaType.AVRO, {"fields": []}, {"fields": [new_field]})
    assert result.result is expected
    assert result.authoritative is False
    assert result.limitations


def test_avro_widening_and_enum_removal():
    widened = evaluate(
        SchemaType.AVRO, {"fields": [{"name": "x", "type": "int"}]}, {"fields": [{"name": "x", "type": "long"}]}
    )
    assert widened.result is CompatibilityResult.COMPATIBLE
    enum = evaluate(
        SchemaType.AVRO,
        {"fields": [{"name": "x", "symbols": ["A", "B"]}]},
        {"fields": [{"name": "x", "symbols": ["A"]}]},
    )
    assert enum.result is CompatibilityResult.INCOMPATIBLE


def test_json_schema_requiredness_and_property_changes():
    old = {"properties": {"a": {"type": "string"}}, "required": []}
    new = {"properties": {"a": {"type": "integer"}, "b": {"type": "string"}}, "required": ["b"]}
    result = evaluate(SchemaType.JSON_SCHEMA, old, new)
    assert set(result.change_set.summary.change_categories) == {
        "field_requiredness_changed",
        "field_type_changed",
        "json_property_added",
    }
    assert result.result is CompatibilityResult.INCOMPATIBLE


def test_protobuf_descriptor_rules_detect_number_reuse_type_change_and_messages():
    old = {"messages": {"M": {"fields": [{"number": 1, "name": "old", "type": "string"}]}, "Removed": {"fields": []}}}
    new = {"messages": {"M": {"fields": [{"number": 1, "name": "new", "type": "int32"}]}, "Added": {"fields": []}}}
    result = evaluate(SchemaType.PROTOBUF, old, new)
    assert result.result is CompatibilityResult.INCOMPATIBLE
    assert {"protobuf_field_number_changed", "protobuf_field_type_changed", "message_added", "message_removed"} <= set(
        result.change_set.summary.change_categories
    )


def test_unknown_unsupported_and_missing_prior_are_not_compatible():
    assert evaluate(SchemaType.UNKNOWN, {}, {}).result is CompatibilityResult.UNSUPPORTED
    assert evaluate(SchemaType.AVRO, None, {}).result is CompatibilityResult.UNKNOWN
    assert (
        evaluate_schema_change(SchemaType.AVRO, CompatibilityPolicy.UNKNOWN, {}, {}, hash_salt="x").result
        is CompatibilityResult.UNKNOWN
    )


def test_raw_schema_size_is_bounded_and_error_does_not_echo_content():
    sentinel = "HIGHLY-SENSITIVE-BUSINESS-DESCRIPTION"
    assert sentinel not in fingerprint_schema({"doc": sentinel})
    with pytest.raises(ValueError, match="^schema_too_large$") as error:
        fingerprint_schema(sentinel.encode() * 20_000)
    assert sentinel not in str(error.value)


def test_subject_binding_never_guesses_ambiguous_record_names():
    topics = {"orders": "resource-1"}
    key = resolve_kafka_subject_binding("orders-key", topics, naming_strategy="TopicNameStrategy")
    assert (key.resource_id, key.schema_role, key.binding_confidence) == ("resource-1", "message_key", 0.95)
    assert (
        resolve_kafka_subject_binding("com.example.Order", topics, naming_strategy="RecordNameStrategy").resource_id
        is None
    )
    assert (
        resolve_kafka_subject_binding(
            "orders-com.example.Order", topics, naming_strategy="TopicRecordNameStrategy"
        ).binding_confidence
        == 0
    )
    assert resolve_kafka_subject_binding("orders-value", topics).resource_id is None
    assert resolve_kafka_subject_binding("anything", topics, reviewed_resource_id="resource-2").binding_confidence == 1


def _consumer():
    return SchemaApplicationBinding(
        "consumer-a", "resource-1", "subject-1", "consumer", datetime.now(timezone.utc), "instrumentation", 1.0
    )


def test_breaking_change_only_means_potential_exposure_without_runtime_evidence():
    evaluation = evaluate(SchemaType.AVRO, {"fields": []}, {"fields": [{"name": "x", "type": "string"}]})
    exposure = evaluate_consumer_exposure(_consumer(), evaluation)
    assert exposure.exposure_state is ExposureState.POTENTIALLY_EXPOSED
    assert exposure.compatibility_state is CompatibilityResult.UNKNOWN


def test_consumer_incompatibility_degradation_and_recovery_require_independent_evidence():
    evaluation = evaluate(SchemaType.AVRO, {"fields": []}, {"fields": [{"name": "x", "type": "string"}]})
    assert (
        evaluate_consumer_exposure(_consumer(), evaluation, proven_incompatible=True).exposure_state
        is ExposureState.INCOMPATIBLE
    )
    change = datetime(2026, 1, 1, tzinfo=timezone.utc)
    degraded = evaluate_consumer_exposure(
        _consumer(),
        evaluation,
        runtime_schema_error_count=3,
        schema_change_at=change,
        degradation_observed_at=change + timedelta(seconds=83),
    )
    assert degraded.exposure_state is ExposureState.DEGRADATION_OBSERVED
    assert degraded.delta_seconds == 83
    assert (
        evaluate_consumer_exposure(_consumer(), evaluation, recovering=True).exposure_state is ExposureState.RECOVERING
    )


def test_temporal_wording_does_not_claim_causality():
    text = temporal_correlation_text("Consumer error rate", 120, 14)
    assert text == "Consumer error rate increased 120 seconds after schema version 14 was observed."
    assert all(term not in text.lower() for term in ("caused by", "root cause", "confirmed cause"))
