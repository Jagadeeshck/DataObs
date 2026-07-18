from __future__ import annotations

import hashlib
import json
import re


def normalise_type(t: str) -> str:
    t = t.lower()
    if "int" in t:
        return "integer"
    if any(x in t for x in ["char", "text", "uuid"]):
        return "string"
    if any(x in t for x in ["timestamp", "date", "time"]):
        return "timestamp"
    if any(x in t for x in ["numeric", "decimal", "double", "real", "money"]):
        return "number"
    if "bool" in t:
        return "boolean"
    return t


def normalise_default(v):
    if v is None:
        return None
    return re.sub(r"::[a-zA-Z0-9_ .\[\]]+", "", str(v)).strip()


def canonicalize_schema(schema):
    out = {**schema}
    out["columns"] = sorted(
        [
            {
                **c,
                "type": normalise_type(c.get("type") or c.get("native_type", "")),
                "default": normalise_default(c.get("default")),
            }
            for c in schema.get("columns", [])
        ],
        key=lambda c: c["name"],
    )
    for key in ("constraints", "indexes", "partitions"):
        out[key] = sorted(schema.get(key, []), key=lambda x: json.dumps(x, sort_keys=True))
    return out


def schema_fingerprint(canonical):
    return hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
