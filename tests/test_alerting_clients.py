from src.alerting.pagerduty import PagerDutyClient, PagerDutyConfig, PagerDutyEvent
from src.alerting.slack import SlackClient, SlackConfig, SlackEvent


def test_pagerduty_payload_has_required_fields():
    client = PagerDutyClient(PagerDutyConfig(routing_key="rk", source="dataobs-tests"))
    payload = client._payload(
        PagerDutyEvent(
            summary="Freshness breach",
            severity="critical",
            component="quality-engine",
            dedup_key="orders-freshness",
            custom_details={"dataset": "prod.orders"},
        )
    )

    assert payload["routing_key"] == "rk"
    assert payload["payload"]["severity"] == "critical"
    assert payload["payload"]["custom_details"]["dataset"] == "prod.orders"


def test_slack_payload_includes_dataset_and_runbook():
    client = SlackClient(SlackConfig(webhook_url="https://hooks.slack.test", default_channel="#alerts"))
    payload = client._payload(
        SlackEvent(
            title="Data freshness alert",
            text="orders table is stale",
            severity="high",
            dataset="prod.orders",
            runbook_url="https://runbooks/dataobs/freshness",
        )
    )

    fields = payload["attachments"][0]["fields"]
    assert payload["channel"] == "#alerts"
    assert any(f["title"] == "Dataset" for f in fields)
    assert any(f["title"] == "Runbook" for f in fields)
