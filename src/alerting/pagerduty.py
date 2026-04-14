"""PagerDuty Events API integration for DataObs alerts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Optional
from urllib import request


@dataclass
class PagerDutyConfig:
    routing_key: str
    source: str = "dataobs"
    events_api_url: str = "https://events.pagerduty.com/v2/enqueue"
    timeout_seconds: int = 10

    def __repr__(self) -> str:  # prevent routing_key leaking into logs
        return (
            f"PagerDutyConfig(routing_key='***', source={self.source!r}, "
            f"events_api_url={self.events_api_url!r})"
        )


@dataclass
class PagerDutyEvent:
    summary: str
    severity: str
    component: str
    group: str = "data-observability"
    class_type: str = "dataops"
    dedup_key: Optional[str] = None
    custom_details: dict | None = None


class PagerDutyClient:
    def __init__(self, config: PagerDutyConfig):
        self.config = config

    def _payload(self, event: PagerDutyEvent) -> dict:
        return {
            "routing_key": self.config.routing_key,
            "event_action": "trigger",
            "dedup_key": event.dedup_key,
            "payload": {
                "summary": event.summary,
                "source": self.config.source,
                "severity": event.severity,
                "component": event.component,
                "group": event.group,
                "class": event.class_type,
                "custom_details": event.custom_details or {},
            },
        }

    def trigger(self, event: PagerDutyEvent) -> dict:
        req = request.Request(
            self.config.events_api_url,
            data=json.dumps(self._payload(event)).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )
        with request.urlopen(req, timeout=self.config.timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
