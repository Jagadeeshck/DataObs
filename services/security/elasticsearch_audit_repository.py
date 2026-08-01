from .audit_repository import SECURITY_ACTIONS, SECURITY_EVENT_DATA_STREAM, SecurityAuditEvent


class ElasticsearchAuditRepository:
    def __init__(self, client, *, request_timeout: float = 10.0):
        self.client, self.request_timeout = client, request_timeout

    def append(self, event: SecurityAuditEvent) -> None:
        if event.event_action not in SECURITY_ACTIONS:
            raise ValueError("unsupported security audit action")
        document = {("@timestamp" if k == "timestamp" else k): v for k, v in event.__dict__.items() if v is not None}
        self.client.index(
            index=SECURITY_EVENT_DATA_STREAM,
            document=document,
            op_type="create",
            refresh="wait_for",
            request_timeout=self.request_timeout,
        )
