"""Conservative JSON/OpenAPI contract comparison without executing input."""

from __future__ import annotations

from typing import Any


def compare_schema(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    changes = []
    old_props, new_props = old.get("properties", {}), new.get("properties", {})
    for name in sorted(old_props.keys() - new_props.keys()):
        changes.append({"code": "FIELD_REMOVED", "path": name, "classification": "breaking"})
    for name in sorted(new_props.keys() - old_props.keys()):
        required = name in new.get("required", [])
        changes.append(
            {
                "code": "REQUIRED_FIELD_ADDED" if required else "OPTIONAL_FIELD_ADDED",
                "path": name,
                "classification": "breaking" if required else "non_breaking",
            }
        )
    for name in sorted(old_props.keys() & new_props.keys()):
        before, after = old_props[name], new_props[name]
        if before.get("type") != after.get("type"):
            changes.append({"code": "TYPE_CHANGED", "path": name, "classification": "breaking"})
        if set(after.get("enum", [])) < set(before.get("enum", [])):
            changes.append({"code": "ENUM_NARROWED", "path": name, "classification": "breaking"})
    return {
        "classification": "breaking" if any(c["classification"] == "breaking" for c in changes) else "non_breaking",
        "changes": changes,
    }


def compare_openapi(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    changes = []
    for route in sorted(old.get("paths", {}).keys() - new.get("paths", {}).keys()):
        changes.append({"code": "ROUTE_REMOVED", "path": route, "classification": "breaking"})
    for route in sorted(old.get("paths", {}).keys() & new.get("paths", {}).keys()):
        for method in sorted(old["paths"][route].keys() - new["paths"][route].keys()):
            changes.append(
                {"code": "METHOD_REMOVED", "path": f"{method.upper()} {route}", "classification": "breaking"}
            )
    for route in sorted(new.get("paths", {}).keys() - old.get("paths", {}).keys()):
        changes.append({"code": "ROUTE_ADDED", "path": route, "classification": "non_breaking"})
    return {
        "classification": "breaking" if any(c["classification"] == "breaking" for c in changes) else "non_breaking",
        "changes": changes,
    }
