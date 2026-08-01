from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from .normalizer import fingerprint


class SchemaRegistryCollector:
    def __init__(self, client: Any, *, maximum_subjects: int = 1000, maximum_versions: int = 100):
        self.client = client
        self.maximum_subjects = maximum_subjects
        self.maximum_versions = maximum_versions

    def collect(self) -> dict[str, Any]:
        subjects = sorted(self.client.subjects())
        selected = subjects[: self.maximum_subjects]
        rows: list[dict[str, Any]] = []
        for subject in selected:
            compatibility = self.client.compatibility(subject).get("compatibilityLevel", "UNKNOWN")
            for version in self.client.versions(subject)[-self.maximum_versions :]:
                item = self.client.schema(subject, version)
                raw = item.get("schema", "")
                rows.append(
                    {
                        "subject_id": subject,
                        "subject": subject,
                        "version": version,
                        "schema_id": item.get("id"),
                        "schema_type": item.get("schemaType", "AVRO").upper(),
                        "fingerprint": fingerprint(raw),
                        "references": item.get("references", []),
                        "compatibility_mode": compatibility,
                        "semantic_summary": _summary(raw),
                        "observed_at": datetime.now(timezone.utc).isoformat(),
                    }
                )
        return {
            "schemas": rows,
            "continuation": selected[-1] if len(subjects) > len(selected) and selected else None,
            "data_status": "partial" if len(subjects) > len(selected) else "complete",
        }


def _summary(raw: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return {"format": "protobuf", "field_count": raw.count("=")}
    fields: Any = value.get("fields", value.get("properties", {})) if isinstance(value, dict) else {}
    if not isinstance(fields, (list, dict)):
        fields = []
    return {
        "format": "structured",
        "field_count": len(fields),
        "name": value.get("name") if isinstance(value, dict) else None,
    }
