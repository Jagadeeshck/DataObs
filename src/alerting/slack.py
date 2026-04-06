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
        color = {
            "critical": "#D7263D",
            "high": "#F46036",
            "medium": "#2E86AB",
            "low": "#2A9D8F",
        }.get(event.severity.lower(), "#2E86AB")

        fields = [{"title": "Severity", "value": event.severity, "short": True}]
        if event.dataset:
            fields.append({"title": "Dataset", "value": event.dataset, "short": True})
        if event.runbook_url:
            fields.append({"title": "Runbook", "value": event.runbook_url, "short": False})

        payload = {
            "username": self.config.username,
            "icon_emoji": self.config.icon_emoji,
            "attachments": [
                {
                    "fallback": event.title,
                    "color": color,
                    "title": event.title,
                    "text": event.text,
                    "fields": fields,
                }
            ],
        }

        payload["channel"] = event.channel or self.config.default_channel
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
