from __future__ import annotations


def classify_change(schema_type: str, previous: dict, current: dict) -> dict:
    kind = schema_type.upper()
    rules = []
    if kind in {"AVRO", "JSON"}:
        old_required = set(previous.get("required", []))
        new_required = set(current.get("required", []))
        if kind == "AVRO":
            old_fields = {f["name"]: f for f in previous.get("fields", [])}
            new_fields = {f["name"]: f for f in current.get("fields", [])}
            removed = set(old_fields) - set(new_fields)
            added_without_default = {n for n in set(new_fields) - set(old_fields) if "default" not in new_fields[n]}
            if removed:
                rules.append({"id": "field_removed", "fields": sorted(removed)})
            if added_without_default:
                rules.append({"id": "required_field_added", "fields": sorted(added_without_default)})
        elif new_required - old_required:
            rules.append({"id": "required_property_added", "fields": sorted(new_required - old_required)})
    elif kind == "PROTOBUF":
        old = {f.get("number"): f.get("name") for f in previous.get("fields", [])}
        new = {f.get("number"): f.get("name") for f in current.get("fields", [])}
        reused = {number for number in old.keys() & new.keys() if old[number] != new[number]}
        if reused:
            rules.append({"id": "field_number_reused", "numbers": sorted(reused)})
    else:
        return {"classification": "unknown", "rules": [{"id": "unsupported_schema_type"}]}
    return {"classification": "breaking" if rules else "compatible", "rules": rules}
