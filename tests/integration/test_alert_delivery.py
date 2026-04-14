"""
Integration tests for alert delivery paths.
Uses unittest.mock to intercept HTTP calls to Slack/PagerDuty/ServiceNow.

Resolves: https://github.com/Jagadeeshck/DataObs/issues/25
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from src.alerting.slack import SlackClient
from src.alerting.pagerduty import PagerDutyClient
from src.alerting.servicenow import ServiceNowClient


SAMPLE_ALERT = {
    "check_name": "null_check",
    "table": "transactions",
    "column": "amount",
    "status": "failed",
    "score": 0.22,
    "message": "Null rate 22% exceeds threshold 5%",
}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_slack_alert_delivery() -> None:
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 200
        client = SlackClient(webhook_url="https://hooks.slack.com/test")
        await client.send_alert(SAMPLE_ALERT)
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs.args[1]
        assert "null_check" in str(payload)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pagerduty_alert_delivery() -> None:
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 202
        client = PagerDutyClient(integration_key="test-key")
        await client.send_alert(SAMPLE_ALERT)
        mock_post.assert_called_once()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_servicenow_incident_creation() -> None:
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 201
        mock_post.return_value.json = lambda: {"result": {"sys_id": "abc123"}}
        client = ServiceNowClient(
            instance_url="https://test.service-now.com",
            username="admin",
            password="secret",
        )
        await client.send_alert(SAMPLE_ALERT)
        mock_post.assert_called_once()
