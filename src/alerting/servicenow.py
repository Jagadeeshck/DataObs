"""ServiceNow alert routing for DataObs incidents."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Dict, Optional
from urllib import request


@dataclass
class ServiceNowConfig:
    instance_url: str
    username: str
    password: str
    table: str = "incident"
    timeout_seconds: int = 10
    severity_to_priority: Dict[str, str] | None = None

    def __repr__(self) -> str:  # prevent password leaking into logs
        return (
            f"ServiceNowConfig(instance_url={self.instance_url!r}, "
            f"username={self.username!r}, password='***', table={self.table!r})"
        )


@dataclass
class AlertEvent:
    title: str
    description: str
    severity: str
    source: str
    dataset: Optional[str] = None
    runbook_url: Optional[str] = None


class ServiceNowClient:
    """Small wrapper to create/update incidents in ServiceNow."""

    def __init__(self, config: ServiceNowConfig):
        self.config = config
        if self.config.severity_to_priority is None:
            self.config.severity_to_priority = {
                "critical": "1",
                "high": "2",
                "medium": "3",
                "low": "4",
            }

    def _endpoint(self) -> str:
        return f"{self.config.instance_url.rstrip('/')}/api/now/table/{self.config.table}"

    def _payload(self, event: AlertEvent) -> dict:
        priority = self.config.severity_to_priority.get(event.severity.lower(), "3")
        description = event.description
        if event.dataset:
            description += f"\nDataset: {event.dataset}"
        if event.runbook_url:
            description += f"\nRunbook: {event.runbook_url}"

        return {
            "short_description": event.title,
            "description": description,
            "priority": priority,
            "category": "Data Observability",
            "u_dataobs_source": event.source,
            "u_dataobs_severity": event.severity.lower(),
        }

    def create_incident(self, event: AlertEvent) -> str:
        payload = json.dumps(self._payload(event)).encode("utf-8")
        auth = base64.b64encode(f"{self.config.username}:{self.config.password}".encode("utf-8")).decode("ascii")
        req = request.Request(
            self._endpoint(),
            data=payload,
            method="POST",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Basic {auth}",
            },
        )
        with request.urlopen(req, timeout=self.config.timeout_seconds) as response:
            body = json.loads(response.read().decode("utf-8"))
        return body["result"]["number"]
