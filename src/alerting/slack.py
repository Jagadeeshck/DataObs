"""Slack Incoming Webhook integration for DataObs alerts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional
from urllib import request


@dataclass
class SlackConfig:
    webhook_url: str
    default_channel: Optional[str] = None
    username: str = "DataObs"
    icon_emoji: str = ":satellite:"
    timeout_seconds: int = 10

    def __repr__(self) -> str:  # prevent webhook_url leaking into logs
        return (
            f"SlackConfig(webhook_url='***', default_channel={self.default_channel!r}, "
            f"username={self.username!r})"
        )


@dataclass
class SlackEvent:
    title: str
    text: str
    severity: str
    dataset: Optional[str] = None
    runbook_url: Optional[str] = None
    channel: Optional[str] = None


class SlackClient:
    def __init__(self, config: SlackConfig):
        self.config = config

    def _payload(self, event: SlackEvent) -> dict:
        """Build a Block Kit payload (replaces deprecated attachments API)."""
        color = {
            "critical": "#D7263D",
            "high": "#F46036",
            "medium": "#2E86AB",
            "low": "#2A9D8F",
        }.get(event.severity.lower(), "#2E86AB")

        # Header block
        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": event.title, "emoji": True},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": event.text},
            },
        ]

        # Fields block — severity + optional dataset
        fields = [
            {"type": "mrkdwn", "text": f"*Severity*\n{event.severity.upper()}"},
        ]
        if event.dataset:
            fields.append({"type": "mrkdwn", "text": f"*Dataset*\n{event.dataset}"})
        blocks.append({"type": "section", "fields": fields})

        # Runbook context block
        if event.runbook_url:
            blocks.append({
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f":notebook: *Runbook:* <{event.runbook_url}|View runbook>"}
                ],
            })

        # Coloured attachment wrapper (Block Kit doesn't support colour natively;
        # wrapping in an attachment preserves the left-side colour stripe)
        payload: dict = {
            "username": self.config.username,
            "icon_emoji": self.config.icon_emoji,
            "attachments": [
                {
                    "color": color,
                    "blocks": blocks,
                    "fallback": event.title,
                }
            ],
        }

        channel = event.channel or self.config.default_channel
        if channel:
            payload["channel"] = channel
        return payload

    def send(self, event: SlackEvent) -> dict:
        req = request.Request(
            self.config.webhook_url,
            data=json.dumps(self._payload(event)).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with request.urlopen(req, timeout=self.config.timeout_seconds) as response:
            body = response.read().decode("utf-8").strip()
        return {"status": "ok" if body.lower() == "ok" else body}
