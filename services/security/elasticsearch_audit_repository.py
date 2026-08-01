from typing import Any

from src.security.redaction import redact

from .audit_repository import SECURITY_ACTIONS, AuditEvent

# Concrete append target within the exact 0020 data-stream family.
SECURITY_EVENT_DATA_STREAM = "logs-dataobs.security-event-default"


class ElasticsearchAuditRepository:
    def __init__(self, client: Any, *, request_timeout: float = 10.0):
        self.client, self.request_timeout = client, request_timeout

    def append(self, event: AuditEvent) -> None:
        if event.event_action not in SECURITY_ACTIONS:
            raise ValueError("unsupported security event action")
        self.client.create(
            index=SECURITY_EVENT_DATA_STREAM, document=redact(event.document()), request_timeout=self.request_timeout
        )
