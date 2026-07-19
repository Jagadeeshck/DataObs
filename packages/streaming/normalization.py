from typing import Any

from .redaction import safe_topic_config


def normalize_kafka_topic(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": str(raw["name"]),
        "internal": bool(raw.get("internal", False)),
        "partition_count": int(raw.get("partition_count", 0)),
        "config": safe_topic_config(raw.get("config", {})),
    }
