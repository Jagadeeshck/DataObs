"""Pure streaming schema compatibility and consumer-impact intelligence.

Raw schemas are accepted only as transient inputs to :func:`evaluate_schema_change`.
The returned contracts contain counts, categories, and salted field-path hashes;
they never retain schema bodies, field names, defaults, or documentation.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Iterable, Mapping, Sequence

MAX_SUBJECTS_PER_CYCLE = 1_000
MAX_VERSIONS_PER_SUBJECT = 100
MAX_VERSIONS_PER_EVALUATION = 25
MAX_SCHEMA_BYTES = 256 * 1024


class SchemaType(str, Enum):
    AVRO = "AVRO"
    PROTOBUF = "PROTOBUF"
    JSON_SCHEMA = "JSON_SCHEMA"
    UNKNOWN = "UNKNOWN"


class CompatibilityPolicy(str, Enum):
    NONE = "NONE"
    BACKWARD = "BACKWARD"
    BACKWARD_TRANSITIVE = "BACKWARD_TRANSITIVE"
    FORWARD = "FORWARD"
    FORWARD_TRANSITIVE = "FORWARD_TRANSITIVE"
    FULL = "FULL"
    FULL_TRANSITIVE = "FULL_TRANSITIVE"
    UNKNOWN = "UNKNOWN"


class CompatibilityResult(str, Enum):
    COMPATIBLE = "compatible"
    COMPATIBLE_WITH_WARNINGS = "compatible_with_warnings"
    INCOMPATIBLE = "incompatible"
    UNKNOWN = "unknown"
    UNSUPPORTED = "unsupported"
    EVALUATION_UNAVAILABLE = "evaluation_unavailable"


class ChangeSeverity(str, Enum):
    INFORMATIONAL = "informational"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class ExposureState(str, Enum):
    NOT_EXPOSED = "not_exposed"
    POTENTIALLY_EXPOSED = "potentially_exposed"
    LIKELY_COMPATIBLE = "likely_compatible"
    INCOMPATIBLE = "incompatible"
    DEGRADATION_OBSERVED = "degradation_observed"
    RECOVERING = "recovering"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class SchemaIdentity:
    tenant_id: str
    environment: str
    registry_id: str
    subject: str

    @property
    def subject_id(self) -> str:
        return _stable_id("schema_subject", self.tenant_id, self.environment, self.registry_id, self.subject)

    def version_id(self, version: int, fingerprint: str) -> str:
        return _stable_id("schema_version", self.subject_id, version, fingerprint)


@dataclass(frozen=True)
class SchemaSubjectRef:
    subject_id: str
    schema_type: SchemaType
    source_compatibility_value: str | None = None


@dataclass(frozen=True)
class SchemaVersionRef:
    subject_id: str
    version: int
    fingerprint: str
    observed_at: datetime


@dataclass(frozen=True)
class SchemaFieldIdentity:
    field_path_hash: str


@dataclass(frozen=True)
class SchemaStructuralSummary:
    changed_field_count: int = 0
    added_field_count: int = 0
    removed_field_count: int = 0
    type_change_count: int = 0
    requiredness_change_count: int = 0
    change_categories: tuple[str, ...] = ()


@dataclass(frozen=True)
class SchemaChange:
    category: str
    field: SchemaFieldIdentity | None = None


@dataclass(frozen=True)
class SchemaChangeSet:
    changes: tuple[SchemaChange, ...]
    summary: SchemaStructuralSummary
    schema_change_severity: ChangeSeverity


@dataclass(frozen=True)
class CompatibilityEvaluation:
    schema_type: SchemaType
    policy: CompatibilityPolicy
    result: CompatibilityResult
    method: str
    authoritative: bool
    confidence: float
    change_set: SchemaChangeSet
    limitations: tuple[str, ...] = ()
    missing_inputs: tuple[str, ...] = ()


@dataclass(frozen=True)
class SchemaResourceBinding:
    resource_id: str | None
    schema_role: str
    binding_method: str
    binding_confidence: float


@dataclass(frozen=True)
class SchemaApplicationBinding:
    application_id: str
    resource_id: str
    subject_id: str
    usage_role: str
    observed_at: datetime
    binding_method: str
    confidence: float
    schema_version: int | None = None
    consumer_group_or_subscription: str | None = None
    supported_schema_versions: tuple[int, ...] = ()
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class ConsumerSchemaExposure:
    consumer_id: str
    exposure_state: ExposureState
    compatibility_state: CompatibilityResult
    reason_codes: tuple[str, ...]
    observed_schema_errors: int | None = None
    delta_seconds: int | None = None
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProducerSchemaExposure:
    application_id: str
    subject_id: str
    schema_version: int | None
    confidence: float


@dataclass(frozen=True)
class SchemaPathwayImpact:
    pathway_ids: tuple[str, ...] = ()
    downstream_resource_ids: tuple[str, ...] = ()
    bounded: bool = True


@dataclass(frozen=True)
class SchemaProductImpact:
    status: str = "unavailable"
    potentially_exposed_products: tuple[str, ...] = ()
    observed_product_degradation: tuple[str, ...] = ()


@dataclass(frozen=True)
class SchemaEvidenceCompleteness:
    status: str
    confidence: float
    missing_inputs: tuple[str, ...] = ()


def normalize_schema_type(value: str | None) -> SchemaType:
    normalized = (value or "").upper().replace("-", "_")
    if normalized == "JSON":
        normalized = "JSON_SCHEMA"
    return SchemaType(normalized) if normalized in SchemaType._value2member_map_ else SchemaType.UNKNOWN


def normalize_policy(value: str | None) -> CompatibilityPolicy:
    normalized = (value or "").upper().replace("-", "_")
    return (
        CompatibilityPolicy(normalized)
        if normalized in CompatibilityPolicy._value2member_map_
        else CompatibilityPolicy.UNKNOWN
    )


def fingerprint_schema(schema: bytes | str | Mapping[str, Any]) -> str:
    """Fingerprint transient material without retaining or returning it."""
    if isinstance(schema, Mapping):
        material = json.dumps(schema, sort_keys=True, separators=(",", ":")).encode()
    elif isinstance(schema, str):
        material = schema.encode()
    else:
        material = schema
    if len(material) > MAX_SCHEMA_BYTES:
        raise ValueError("schema_too_large")
    return hashlib.sha256(material).hexdigest()


def evaluate_schema_change(
    schema_type: SchemaType,
    policy: CompatibilityPolicy,
    previous: Mapping[str, Any] | None,
    current: Mapping[str, Any] | None,
    *,
    hash_salt: str,
) -> CompatibilityEvaluation:
    """Evaluate safe structural metadata from in-memory parsed schema objects."""
    empty = SchemaChangeSet((), SchemaStructuralSummary(), ChangeSeverity.UNKNOWN)
    if previous is None:
        return CompatibilityEvaluation(
            schema_type,
            policy,
            CompatibilityResult.UNKNOWN,
            "unavailable",
            False,
            0,
            empty,
            missing_inputs=("previous_version",),
        )
    if current is None:
        return CompatibilityEvaluation(
            schema_type,
            policy,
            CompatibilityResult.EVALUATION_UNAVAILABLE,
            "unavailable",
            False,
            0,
            empty,
            missing_inputs=("current_schema",),
        )
    if schema_type is SchemaType.UNKNOWN:
        return CompatibilityEvaluation(
            schema_type,
            policy,
            CompatibilityResult.UNSUPPORTED,
            "unavailable",
            False,
            0,
            empty,
            ("unsupported_schema_type",),
        )
    if policy is CompatibilityPolicy.UNKNOWN:
        return CompatibilityEvaluation(
            schema_type,
            policy,
            CompatibilityResult.UNKNOWN,
            "structural_heuristic",
            False,
            0.25,
            empty,
            ("compatibility_policy_unknown",),
        )
    changes = _diff(schema_type, previous, current, hash_salt)
    severity = _severity(changes)
    change_set = SchemaChangeSet(tuple(changes), _summary(changes), severity)
    if policy is CompatibilityPolicy.NONE:
        result = CompatibilityResult.COMPATIBLE_WITH_WARNINGS if changes else CompatibilityResult.COMPATIBLE
    else:
        result = CompatibilityResult.INCOMPATIBLE if _breaking(changes, policy) else CompatibilityResult.COMPATIBLE
    limitations = ("local_format_specific_evaluator_not_provider_authoritative",)
    return CompatibilityEvaluation(
        schema_type, policy, result, "dataobs_local_evaluator", False, 0.8, change_set, limitations
    )


def resolve_kafka_subject_binding(
    subject: str,
    known_resource_ids: Mapping[str, str],
    *,
    naming_strategy: str | None = None,
    reviewed_resource_id: str | None = None,
) -> SchemaResourceBinding:
    if reviewed_resource_id:
        return SchemaResourceBinding(reviewed_resource_id, "unknown", "reviewed_mapping", 1.0)
    if naming_strategy == "TopicNameStrategy" and (subject.endswith("-key") or subject.endswith("-value")):
        topic, suffix = subject.rsplit("-", 1)
        return SchemaResourceBinding(
            known_resource_ids.get(topic),
            f"message_{suffix}",
            "topic_name_strategy",
            0.95 if topic in known_resource_ids else 0.0,
        )
    # Record-name subjects cannot be safely mapped without instrumentation.
    method = {
        "RecordNameStrategy": "record_name_strategy_unresolved",
        "TopicRecordNameStrategy": "topic_record_name_strategy_unresolved",
    }.get(naming_strategy, "ambiguous_subject")
    return SchemaResourceBinding(None, "unknown", method, 0.0)


def evaluate_consumer_exposure(
    binding: SchemaApplicationBinding,
    evaluation: CompatibilityEvaluation,
    *,
    proven_compatible: bool = False,
    proven_incompatible: bool = False,
    runtime_schema_error_count: int | None = None,
    recovering: bool = False,
    schema_change_at: datetime | None = None,
    degradation_observed_at: datetime | None = None,
) -> ConsumerSchemaExposure:
    delta = (
        int((degradation_observed_at - schema_change_at).total_seconds())
        if schema_change_at and degradation_observed_at
        else None
    )
    if recovering:
        state, reasons = ExposureState.RECOVERING, ("independent_runtime_recovery_observed",)
    elif runtime_schema_error_count is not None and runtime_schema_error_count > 0:
        state, reasons = ExposureState.DEGRADATION_OBSERVED, ("independent_runtime_schema_errors_observed",)
    elif proven_incompatible:
        state, reasons = ExposureState.INCOMPATIBLE, ("consumer_incompatibility_proven",)
    elif proven_compatible:
        state, reasons = ExposureState.LIKELY_COMPATIBLE, ("consumer_compatibility_proven",)
    elif evaluation.result is CompatibilityResult.INCOMPATIBLE:
        state, reasons = ExposureState.POTENTIALLY_EXPOSED, (
            "breaking_change_consumer_bound",
            "consumer_capability_unknown",
        )
    elif evaluation.result is CompatibilityResult.COMPATIBLE:
        state, reasons = ExposureState.UNKNOWN, ("registry_compatible_consumer_capability_unknown",)
    else:
        state, reasons = ExposureState.UNKNOWN, ("compatibility_evidence_incomplete",)
    compatibility = (
        CompatibilityResult.INCOMPATIBLE
        if proven_incompatible
        else (CompatibilityResult.COMPATIBLE if proven_compatible else CompatibilityResult.UNKNOWN)
    )
    return ConsumerSchemaExposure(
        binding.application_id, state, compatibility, reasons, runtime_schema_error_count, delta, binding.evidence_refs
    )


def temporal_correlation_text(metric_name: str, delta_seconds: int, version: int) -> str:
    return f"{metric_name} increased {delta_seconds} seconds after schema version {version} was observed."


def _stable_id(kind: str, *parts: object) -> str:
    material = "\x1f".join(str(p) for p in (kind, *parts)).encode()
    return f"{kind}_{hashlib.sha256(material).hexdigest()[:32]}"


def _field_hash(salt: str, path: str) -> SchemaFieldIdentity:
    return SchemaFieldIdentity(hashlib.sha256(f"{salt}\x1f{path}".encode()).hexdigest())


def _append(changes: list[SchemaChange], category: str, salt: str, paths: Iterable[str]) -> None:
    changes.extend(SchemaChange(category, _field_hash(salt, path)) for path in sorted(paths))


def _diff(kind: SchemaType, old: Mapping[str, Any], new: Mapping[str, Any], salt: str) -> list[SchemaChange]:
    changes: list[SchemaChange] = []
    if kind is SchemaType.AVRO:
        old_fields = {str(f.get("name")): f for f in old.get("fields", ())}
        new_fields = {str(f.get("name")): f for f in new.get("fields", ())}
        added = new_fields.keys() - old_fields.keys()
        _append(changes, "field_added", salt, added)
        _append(
            changes, "field_requiredness_changed", salt, (name for name in added if "default" not in new_fields[name])
        )
        _append(changes, "field_removed", salt, old_fields.keys() - new_fields.keys())
        for name in old_fields.keys() & new_fields.keys():
            before, after = old_fields[name], new_fields[name]
            if before.get("type") != after.get("type"):
                category = _numeric_type_category(before.get("type"), after.get("type"))
                _append(changes, category, salt, (name,))
            if ("default" in before) != ("default" in after):
                _append(changes, "field_default_presence_changed", salt, (name,))
            old_symbols, new_symbols = set(before.get("symbols", ())), set(after.get("symbols", ()))
            _append(changes, "enum_symbol_added", salt, (f"{name}#{x}" for x in new_symbols - old_symbols))
            _append(changes, "enum_symbol_removed", salt, (f"{name}#{x}" for x in old_symbols - new_symbols))
    elif kind is SchemaType.JSON_SCHEMA:
        old_fields, new_fields = old.get("properties", {}), new.get("properties", {})
        _append(changes, "json_property_added", salt, new_fields.keys() - old_fields.keys())
        _append(changes, "json_property_removed", salt, old_fields.keys() - new_fields.keys())
        for name in old_fields.keys() & new_fields.keys():
            if old_fields[name].get("type") != new_fields[name].get("type"):
                _append(changes, "field_type_changed", salt, (name,))
        required_delta = set(old.get("required", ())) ^ set(new.get("required", ()))
        _append(changes, "field_requiredness_changed", salt, required_delta)
    else:  # parsed protobuf descriptor summary: messages -> fields(number,type)
        old_messages, new_messages = old.get("messages", {}), new.get("messages", {})
        _append(changes, "message_added", salt, new_messages.keys() - old_messages.keys())
        _append(changes, "message_removed", salt, old_messages.keys() - new_messages.keys())
        for message in old_messages.keys() & new_messages.keys():
            old_by_number = {f.get("number"): f for f in old_messages[message].get("fields", ())}
            new_by_number = {f.get("number"): f for f in new_messages[message].get("fields", ())}
            for number in old_by_number.keys() & new_by_number.keys():
                before, after = old_by_number[number], new_by_number[number]
                if before.get("name") != after.get("name"):
                    _append(changes, "protobuf_field_number_changed", salt, (f"{message}.{number}",))
                if before.get("type") != after.get("type"):
                    _append(changes, "protobuf_field_type_changed", salt, (f"{message}.{number}",))
            _append(
                changes, "field_added", salt, (f"{message}.{n}" for n in new_by_number.keys() - old_by_number.keys())
            )
            _append(
                changes, "field_removed", salt, (f"{message}.{n}" for n in old_by_number.keys() - new_by_number.keys())
            )
    return changes


def _numeric_type_category(before: Any, after: Any) -> str:
    order = {"int": 0, "long": 1, "float": 2, "double": 3}
    if before in order and after in order:
        return "field_type_widened" if order[after] > order[before] else "field_type_narrowed"
    return "union_changed" if isinstance(before, list) or isinstance(after, list) else "field_type_changed"


def _breaking(changes: Sequence[SchemaChange], policy: CompatibilityPolicy) -> bool:
    categories = {c.category for c in changes}
    backward = {
        "field_type_narrowed",
        "field_type_changed",
        "union_changed",
        "enum_symbol_removed",
        "field_requiredness_changed",
        "protobuf_field_number_changed",
        "protobuf_field_type_changed",
        "message_removed",
    }
    forward = {
        "field_removed",
        "field_type_widened",
        "field_type_changed",
        "union_changed",
        "enum_symbol_added",
        "protobuf_field_number_changed",
        "protobuf_field_type_changed",
    }
    if policy.value.startswith("BACKWARD"):
        return bool(categories & backward)
    if policy.value.startswith("FORWARD"):
        return bool(categories & forward)
    return bool(categories & (backward | forward))


def _severity(changes: Sequence[SchemaChange]) -> ChangeSeverity:
    categories = {c.category for c in changes}
    if not categories:
        return ChangeSeverity.INFORMATIONAL
    if categories & {"protobuf_field_number_changed", "protobuf_field_type_changed", "message_removed"}:
        return ChangeSeverity.CRITICAL
    if categories & {
        "field_removed",
        "field_type_narrowed",
        "field_type_changed",
        "union_changed",
        "enum_symbol_removed",
        "field_requiredness_changed",
    }:
        return ChangeSeverity.HIGH
    if categories & {"field_added", "json_property_added", "message_added"}:
        return ChangeSeverity.MEDIUM
    return ChangeSeverity.LOW


def _summary(changes: Sequence[SchemaChange]) -> SchemaStructuralSummary:
    categories = tuple(sorted({c.category for c in changes}))
    return SchemaStructuralSummary(
        changed_field_count=len(changes),
        added_field_count=sum(c.category in {"field_added", "json_property_added"} for c in changes),
        removed_field_count=sum(c.category in {"field_removed", "json_property_removed"} for c in changes),
        type_change_count=sum("type_" in c.category or c.category == "union_changed" for c in changes),
        requiredness_change_count=sum(c.category == "field_requiredness_changed" for c in changes),
        change_categories=categories,
    )
