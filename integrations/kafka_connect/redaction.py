from packages.streaming.redaction import redact_mapping

SAFE_CONNECT_FIELDS = {
    "name",
    "connector.class",
    "tasks.max",
    "topics",
    "errors.tolerance",
    "errors.deadletterqueue.topic.name",
    "errors.deadletterqueue.context.headers.enable",
}


def redact_connector_config(config: dict) -> dict:
    return redact_mapping(config, allowlist=SAFE_CONNECT_FIELDS)
