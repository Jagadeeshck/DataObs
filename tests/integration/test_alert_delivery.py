"""Container-backed alert delivery tests for Slack, PagerDuty, and ServiceNow."""

from __future__ import annotations

import pytest

from src.alerting.pagerduty import PagerDutyClient, PagerDutyConfig, PagerDutyEvent
from src.alerting.servicenow import AlertEvent, ServiceNowClient, ServiceNowConfig
from src.alerting.slack import SlackClient, SlackConfig, SlackEvent

MOCK_WEBHOOK = "http://localhost:8089"


@pytest.mark.integration
def test_slack_pagerduty_servicenow_delivery_and_deduplication() -> None:
    dedup_key = "quality-orders-customer_id"

    slack = SlackClient(SlackConfig(webhook_url=f"{MOCK_WEBHOOK}/slack"))
    assert slack.send(SlackEvent("Quality failure", "null-rate drift", "critical", dataset="orders"))["status"] == "ok"

    pagerduty = PagerDutyClient(PagerDutyConfig(routing_key="test", events_api_url=f"{MOCK_WEBHOOK}/pagerduty"))
    pd_result = pagerduty.trigger(
        PagerDutyEvent(
            summary="Quality failure on orders.customer_id",
            severity="critical",
            component="quality-worker",
            dedup_key=dedup_key,
            custom_details={"table": "orders", "column": "customer_id"},
        )
    )
    assert pd_result["dedup_key"] == dedup_key

    servicenow = ServiceNowClient(
        ServiceNowConfig(instance_url=f"{MOCK_WEBHOOK}/servicenow", username="user", password="secret")
    )
    assert (
        servicenow.create_incident(AlertEvent("Quality failure", "null-rate drift", "critical", "dataobs")) == "INC001"
    )
