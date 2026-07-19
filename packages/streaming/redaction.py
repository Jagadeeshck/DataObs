import re
from typing import Any

_SECRET = re.compile(r"(?:password|passwd|secret|token|api[._-]?key|sasl|jaas|private[._-]?key)", re.I)
_SAFE_CONFIGS = {
    "retention.ms",
    "retention.bytes",
    "cleanup.policy",
    "min.insync.replicas",
    "max.message.bytes",
    "compression.type",
    "segment.ms",
    "segment.bytes",
    "unclean.leader.election.enable",
}


def redact_mapping(values: dict[str, Any], *, allowlist: set[str] | None = None) -> dict[str, Any]:
    allowed = allowlist if allowlist is not None else set(values)
    return {key: value for key, value in values.items() if key in allowed and not _SECRET.search(key)}


def safe_topic_config(values: dict[str, Any]) -> dict[str, Any]:
    return redact_mapping(values, allowlist=_SAFE_CONFIGS)
