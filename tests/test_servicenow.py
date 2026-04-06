from src.alerting.servicenow import AlertEvent, ServiceNowClient, ServiceNowConfig


def test_payload_contains_required_dataobs_fields():
    client = ServiceNowClient(
        ServiceNowConfig(instance_url="https://example.service-now.com", username="u", password="p")
    )
    event = AlertEvent(
        title="Freshness breach",
        description="orders table is stale",
        severity="critical",
        source="dataobs.freshness",
        dataset="prod.orders",
        runbook_url="https://runbooks/dataobs/freshness",
    )

    payload = client._payload(event)

    assert payload["short_description"] == "Freshness breach"
    assert payload["priority"] == "1"
    assert payload["u_dataobs_source"] == "dataobs.freshness"
    assert "Dataset: prod.orders" in payload["description"]
