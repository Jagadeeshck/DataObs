"""
Tests for alerting client payload builders.

These tests call internal _payload() methods directly so no real webhook
or API endpoints are hit.
"""

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


def test_pagerduty_repr_masks_routing_key():
    cfg = PagerDutyConfig(routing_key="super-secret-key", source="dataobs")
    assert "super-secret-key" not in repr(cfg)
    assert "***" in repr(cfg)


def test_slack_payload_uses_block_kit_structure():
    """Slack payload must use Block Kit (blocks inside attachments) not legacy fields."""
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

    attachment = payload["attachments"][0]
    # Block Kit: blocks key, not fields key
    assert "blocks" in attachment
    # Colour stripe should still be present
    assert "color" in attachment
    assert attachment["color"] == "#F46036"  # high severity colour


def test_slack_payload_includes_dataset_in_blocks():
    client = SlackClient(SlackConfig(webhook_url="https://hooks.slack.test", default_channel="#alerts"))
    payload = client._payload(
        SlackEvent(
            title="Alert",
            text="stale data",
            severity="high",
            dataset="prod.orders",
        )
    )

    # Flatten all block text to check dataset appears somewhere
    all_text = str(payload)
    assert "prod.orders" in all_text


def test_slack_payload_includes_runbook_in_context_block():
    client = SlackClient(SlackConfig(webhook_url="https://hooks.slack.test"))
    payload = client._payload(
        SlackEvent(
            title="Alert",
            text="stale data",
            severity="critical",
            runbook_url="https://runbooks/dataobs/freshness",
        )
    )

    all_text = str(payload)
    assert "https://runbooks/dataobs/freshness" in all_text


def test_slack_payload_channel_set_from_config():
    client = SlackClient(SlackConfig(webhook_url="https://hooks.slack.test", default_channel="#alerts"))
    payload = client._payload(SlackEvent(title="Alert", text="msg", severity="low"))
    assert payload["channel"] == "#alerts"


def test_slack_repr_masks_webhook_url():
    cfg = SlackConfig(webhook_url="https://hooks.slack.com/T0123/B456/secret")
    assert "secret" not in repr(cfg)
    assert "***" in repr(cfg)
