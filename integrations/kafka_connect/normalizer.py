import hashlib
import json

from .redaction import redact_connector_config


def normalize_connector(name: str, config: dict, status: dict) -> dict:
    safe = redact_connector_config(config)
    return {
        "name": name,
        "connector_type": "source" if "source" in str(config.get("connector.class", "")).lower() else "sink",
        "state": status.get("connector", {}).get("state", "UNKNOWN"),
        "tasks": status.get("tasks", []),
        "config": safe,
        "config_fingerprint": hashlib.sha256(json.dumps(safe, sort_keys=True).encode()).hexdigest(),
    }
