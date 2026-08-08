from __future__ import annotations

from dataclasses import asdict

from .models import SchemaVersion, stable_id, utc_now

_WIDENING = {("smallint", "integer"), ("integer", "bigint"), ("float", "double")}
_NARROWING = {(b, a) for a, b in _WIDENING}


def compare_schemas(previous: SchemaVersion, current: SchemaVersion) -> dict:
    if previous.asset_id != current.asset_id:
        raise ValueError("schema versions must belong to the same asset")
    before = {c.name: c for c in previous.columns}
    after = {c.name: c for c in current.columns}
    added = sorted(after.keys() - before.keys())
    removed = sorted(before.keys() - after.keys())
    types: list[dict] = []
    nullability: list[dict] = []
    constraints: list[dict] = []
    reasons: set[str] = set()
    classifications: list[str] = []
    for name in sorted(before.keys() & after.keys()):
        old, new = before[name], after[name]
        pair = (old.data_type.lower(), new.data_type.lower())
        if pair[0] != pair[1]:
            rule = (
                "type_widened"
                if pair in _WIDENING
                else "type_narrowed" if pair in _NARROWING else "provider_type_unknown"
            )
            types.append({"column": name, "previous": old.data_type, "current": new.data_type, "rule": rule})
            reasons.add(rule)
            classifications.append(
                "compatible"
                if rule == "type_widened"
                else "potentially_breaking" if rule == "type_narrowed" else "unknown"
            )
        if old.nullable != new.nullable:
            rule = "nullability_relaxed" if new.nullable else "nullability_tightened"
            nullability.append({"column": name, "previous": old.nullable, "current": new.nullable, "rule": rule})
            reasons.add(rule)
            classifications.append("compatible" if new.nullable else "potentially_breaking")
        if set(old.constraints) != set(new.constraints):
            constraints.append(
                {
                    "column": name,
                    "added": sorted(set(new.constraints) - set(old.constraints)),
                    "removed": sorted(set(old.constraints) - set(new.constraints)),
                }
            )
            reasons.add("constraint_changed")
            classifications.append("potentially_breaking")
    if removed:
        reasons.add("column_removed")
        classifications.append("breaking")
    if added:
        reasons.add(
            "nullable_column_added" if all(after[n].nullable is not False for n in added) else "required_column_added"
        )
        classifications.append(
            "additive" if all(after[n].nullable is not False for n in added) else "potentially_breaking"
        )
    partition_changes = previous.partition_fields != current.partition_fields
    if partition_changes:
        reasons.add("partition_fields_changed")
        classifications.append("breaking")
    rename_candidates = []
    for old_name in removed:
        for new_name in added:
            if (
                before[old_name].data_type == after[new_name].data_type
                and before[old_name].nullable == after[new_name].nullable
            ):
                rename_candidates.append({"from": old_name, "to": new_name, "relationship": "inferred"})
    priority = ["breaking", "potentially_breaking", "unknown", "additive", "compatible"]
    classification = next((item for item in priority if item in classifications), "metadata_only")
    confidence = min(previous.confidence, current.confidence, 0.6 if rename_candidates else 1.0)
    return {
        "change_id": stable_id("change", previous.asset_id, previous.version_id, current.version_id),
        "asset_id": previous.asset_id,
        "previous_schema_version": previous.version_id,
        "current_schema_version": current.version_id,
        "change_type": classification,
        "severity": {"breaking": "high", "potentially_breaking": "medium", "unknown": "unknown"}.get(
            classification, "low"
        ),
        "compatibility": classification,
        "affected_columns": sorted(set(added + removed + [x["column"] for x in types + nullability + constraints])),
        "added_columns": added,
        "removed_columns": removed,
        "changed_data_types": types,
        "changed_nullability": nullability,
        "changed_constraints": constraints,
        "partition_changes": {
            "changed": partition_changes,
            "previous": list(previous.partition_fields),
            "current": list(current.partition_fields),
        },
        "rename_candidates": rename_candidates,
        "reason_codes": sorted(reasons),
        "confidence": confidence,
        "evidence_refs": sorted(set(previous.evidence_refs + current.evidence_refs)),
        "observed_at": current.observed_at,
        "evaluated_at": utc_now(),
    }
