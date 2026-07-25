from typing import Any, Dict

MAX_FACET_BYTES = 65536


def preserve_facets(payload: Dict[str, Any]) -> Dict[str, Any]:
    import json

    facets = {}
    for entity in ("run", "job", "dataset"):
        value = payload.get(entity) or {}
        if isinstance(value, dict) and isinstance(value.get("facets"), dict):
            facets[entity] = value["facets"]
    for group in ("inputs", "outputs"):
        facets[group] = [x.get("facets", {}) for x in payload.get(group, []) if isinstance(x, dict)]
    if len(json.dumps(facets, default=str).encode()) > MAX_FACET_BYTES:
        raise ValueError("facet budget exceeded")
    return facets
