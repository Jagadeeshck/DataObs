from __future__ import annotations

from typing import Any


def recommend_types(metadata: dict[str, Any]) -> list[tuple[str, str]]:
    """Return monitor type and transparent reason; never applies candidates."""
    candidates = [
        ("volume", "table-like assets require volume coverage"),
        ("schema_change", "schema fingerprint is available"),
    ]
    if metadata.get("timestamp_columns"):
        candidates.append(("freshness", "timestamp column and observed update schedule are available"))
    if metadata.get("primary_key"):
        candidates.append(("field_unique_rate", "declared primary key should remain unique"))
    if metadata.get("nullable_columns"):
        candidates.append(("field_null_rate", "nullable field profile history is available"))
    if metadata.get("pathway_id"):
        candidates.extend(
            [
                ("pathway_latency", "lineage-backed pathway exists"),
                ("consumer_lag", "Kafka consumer group evidence exists"),
            ]
        )
    return candidates
