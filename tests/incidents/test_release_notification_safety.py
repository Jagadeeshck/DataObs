from __future__ import annotations

from src.alerting.dispatcher import AlertDispatcher


class FakeElasticsearch:
    def __init__(self) -> None:
        self.documents: list[dict[str, object]] = []

    def index(self, *, index: str, document: dict[str, object], refresh: str) -> dict[str, str]:
        self.documents.append({"index": index, "document": document, "refresh": refresh})
        return {"result": "created"}


class FailingSlack:
    def __init__(self) -> None:
        self.calls = 0
        self.webhook_secret = "slack-secret-value"

    def send(self, event) -> dict[str, str]:
        self.calls += 1
        raise RuntimeError("password=provider-secret-must-not-persist")


class PagerDutyStub:
    def __init__(self) -> None:
        self.calls = 0
        self.routing_key = "pagerduty-secret-value"

    def trigger(self, event) -> dict[str, str]:
        self.calls += 1
        return {"dedup_key": event.dedup_key, "status": "success"}


class ServiceNowStub:
    def __init__(self) -> None:
        self.calls = 0
        self.password = "servicenow-secret-value"

    def create_incident(self, event) -> str:
        self.calls += 1
        return "INC-TEST-1"


def _finding() -> dict[str, object]:
    return {
        "id": "finding-1",
        "tenant_id": "tenant-a",
        "environment": "production",
        "trace_id": "trace-1",
        "severity": "critical",
        "correlation_id": "execution-1",
        "asset_id": "orders",
        "summary": "quality threshold failed",
    }


def _incident() -> dict[str, object]:
    return {"deduplication_key": "quality:orders:null-rate"}


def test_notification_delivery_is_deduplicated_and_redaction_safe() -> None:
    es = FakeElasticsearch()
    slack = FailingSlack()
    pagerduty = PagerDutyStub()
    servicenow = ServiceNowStub()
    dispatcher = AlertDispatcher(es, slack=slack, pagerduty=pagerduty, servicenow=servicenow)

    first = dispatcher.dispatch(_finding(), _incident(), is_new=True)

    assert {item.channel: item.status for item in first.deliveries} == {
        "slack": "failed",
        "pagerduty": "succeeded",
        "servicenow": "succeeded",
    }
    assert slack.calls == pagerduty.calls == servicenow.calls == 1
    assert len(es.documents) == 3

    persisted = repr(es.documents)
    assert "provider-secret-must-not-persist" not in persisted
    assert "slack-secret-value" not in persisted
    assert "pagerduty-secret-value" not in persisted
    assert "servicenow-secret-value" not in persisted
    assert "RuntimeError" in persisted

    replay = dispatcher.dispatch(_finding(), _incident(), is_new=False)

    assert replay.deduplicated is True
    assert replay.deliveries == ()
    assert slack.calls == pagerduty.calls == servicenow.calls == 1
    assert len(es.documents) == 3


def test_failed_notification_is_not_blindly_retried() -> None:
    es = FakeElasticsearch()
    slack = FailingSlack()
    dispatcher = AlertDispatcher(es, slack=slack)

    result = dispatcher.dispatch(_finding(), _incident(), is_new=True)

    assert slack.calls == 1
    assert result.deliveries[0].status == "failed"
    assert result.deliveries[0].error_type == "RuntimeError"
    assert len(es.documents) == 1
