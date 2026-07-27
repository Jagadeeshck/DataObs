"""Tenant-aware alert orchestration for persisted quality failures."""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from elasticsearch import Elasticsearch
from opentelemetry import trace

from .pagerduty import PagerDutyClient, PagerDutyEvent
from .servicenow import AlertEvent, ServiceNowClient
from .slack import SlackClient, SlackEvent

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DeliveryResult:
    channel: str
    status: str
    reference: str | None = None
    error_type: str | None = None


@dataclass(frozen=True)
class DispatchResult:
    deduplicated: bool
    deliveries: tuple[DeliveryResult, ...]

    @property
    def completely_successful(self) -> bool:
        return bool(self.deliveries) and all(item.status == "succeeded" for item in self.deliveries)


class AlertDispatcher:
    """Deliver a newly-opened incident and persist redaction-safe outcomes."""

    def __init__(
        self,
        es_client: Elasticsearch,
        *,
        slack: SlackClient | None = None,
        pagerduty: PagerDutyClient | None = None,
        servicenow: ServiceNowClient | None = None,
    ) -> None:
        self.es = es_client
        self.slack = slack
        self.pagerduty = pagerduty
        self.servicenow = servicenow

    def dispatch(self, finding: dict[str, Any], incident: dict[str, Any], *, is_new: bool) -> DispatchResult:
        if not is_new:
            return DispatchResult(deduplicated=True, deliveries=())
        correlation = {key: finding.get(key) for key in ("tenant_id", "environment", "trace_id", "severity")}
        correlation.update(
            execution_id=finding.get("correlation_id"),
            dataset=finding.get("asset_id"),
            finding_id=finding["id"],
            deduplication_key=incident["deduplication_key"],
        )
        title = f"Data quality failure: {finding['asset_id']}"
        text = f"{finding['summary']} | correlation={correlation}"
        deliveries: list[DeliveryResult] = []
        channels = (
            ("slack", self.slack, lambda c: c.send(SlackEvent(title, text, finding["severity"], finding["asset_id"]))),
            (
                "pagerduty",
                self.pagerduty,
                lambda c: c.trigger(
                    PagerDutyEvent(
                        title,
                        finding["severity"],
                        "dataobs-quality",
                        dedup_key=incident["deduplication_key"],
                        custom_details=correlation,
                    )
                ),
            ),
            (
                "servicenow",
                self.servicenow,
                lambda c: c.create_incident(
                    AlertEvent(title, text, finding["severity"], "dataobs-quality", finding["asset_id"])
                ),
            ),
        )
        span = trace.get_current_span()
        for channel, client, send in channels:
            if client is None:
                continue
            try:
                response = send(client)
                reference = (
                    response if isinstance(response, str) else response.get("dedup_key") or response.get("status")
                )
                outcome = DeliveryResult(channel, "succeeded", str(reference) if reference else None)
            except Exception as exc:
                outcome = DeliveryResult(channel, "failed", error_type=type(exc).__name__)
            deliveries.append(outcome)
            span.add_event("dataobs.alert.delivery", {"channel": channel, "status": outcome.status})
            logger.info(
                "alert delivery", extra={"channel": channel, "status": outcome.status, "finding_id": finding["id"]}
            )
            self.es.index(
                index="logs-dataobs.notification_delivery-default",
                document={
                    "@timestamp": datetime.now(timezone.utc).isoformat(),
                    **correlation,
                    **asdict(outcome),
                },
                refresh="wait_for",
            )
        return DispatchResult(False, tuple(deliveries))
