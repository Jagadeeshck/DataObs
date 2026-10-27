from __future__ import annotations

from datetime import datetime, timedelta, timezone

from packages.collectors.sdk import (
    Capability,
    CollectionMode,
    ConnectionTestResult,
    PartialFailure,
    ProviderCapabilities,
    ValidationIssue,
    ValidationResult,
)

from .clients import GoogleCloudClientFactory
from .configuration import parse_gcp_configuration
from .errors import GoogleCloudCollectorError
from .evidence import metric
from .monitoring import ALLOWED_METRICS, REGIONAL_BACKLOG_METRICS, collect_metric_series, point_value
from .services.pubsub import collect_project

SERVICES = frozenset({"pubsub"})
LIMITATIONS = (
    "Pub/Sub Lite, payloads, snapshots, IAM policies, schema bodies, and resource mutation are unsupported",
    "Cloud Monitoring is provider-native evidence; Team 1 does not yet project every metric family",
    "Hosted live Google Cloud IAM and Monitoring validation has not been performed",
)


class GoogleCloudMessagingProvider:
    provider_type = "gcp"
    provider_version = "1"

    def __init__(self, client_factory=None):
        self._client_factory = client_factory or GoogleCloudClientFactory()
        self._configuration = None

    def capabilities(self):
        supported = frozenset(
            {
                Capability.RESOURCE_DISCOVERY,
                Capability.METADATA_COLLECTION,
                Capability.METRIC_COLLECTION,
                Capability.HEALTH_CHECK,
                Capability.INCREMENTAL_COLLECTION,
            }
        )
        return ProviderCapabilities(
            supported,
            frozenset(set(Capability) - set(supported)),
            ("roles/pubsub.viewer", "roles/monitoring.viewer"),
            frozenset({CollectionMode.SCHEDULED, CollectionMode.ON_DEMAND}),
            ("google-cloud-pubsub", "google-cloud-monitoring", "google-auth"),
            LIMITATIONS,
        )

    async def validate_configuration(self, context, configuration):
        try:
            self._configuration = parse_gcp_configuration(configuration)
            return ValidationResult(True)
        except GoogleCloudCollectorError as exc:
            return ValidationResult(
                False, (ValidationIssue(exc.code, exc.family, "Google Cloud configuration is invalid"),)
            )

    async def test_connection(self, context, configuration):
        try:
            cfg = parse_gcp_configuration(configuration)
            publisher, subscriber, _ = self._client_factory.create(cfg)
            project = cfg.projects[0].project_id
            list(
                publisher.invoke(
                    "list_topics",
                    request={"project": f"projects/{project}", "page_size": 1},
                    timeout=cfg.limits["request_timeout_seconds"],
                )
            )
            list(
                subscriber.invoke(
                    "list_subscriptions",
                    request={"project": f"projects/{project}", "page_size": 1},
                    timeout=cfg.limits["request_timeout_seconds"],
                )
            )
            return ConnectionTestResult(True, 0)
        except GoogleCloudCollectorError as exc:
            return ConnectionTestResult(False, error_code=exc.code, message="Google Cloud connection test failed")

    async def discover(self, context, request):
        async for item in self.collect(context, request):
            if not isinstance(item, PartialFailure):
                yield item

    async def collect(self, context, request):
        self.capabilities().require(request.capabilities)
        if self._configuration is None:
            raise RuntimeError("configuration must be validated before collection")
        try:
            publisher, subscriber, monitoring = self._client_factory.create(self._configuration)
        except GoogleCloudCollectorError as exc:
            yield PartialFailure(
                "resource_discovery", exc.code, "Google Cloud dependencies or credentials unavailable", exc.retryable
            )
            return
        emitted = 0
        for project in self._configuration.projects:
            resources = []
            try:
                for observation in collect_project(context, self._configuration, project, publisher, subscriber):
                    resources.append(observation)
                    emitted += 1
                    if emitted > self._configuration.limits["maximum_observations"]:
                        yield PartialFailure(
                            "metadata_collection", "result_truncated", "Google Cloud observation limit reached", False
                        )
                        return
                    yield observation
            except GoogleCloudCollectorError as exc:
                yield PartialFailure(
                    "metadata_collection", exc.code, "Google Cloud project collection partially failed", exc.retryable
                )
            except Exception:
                yield PartialFailure(
                    "metadata_collection",
                    "partial_collection_failure",
                    "Google Cloud project collection partially failed",
                    False,
                )
            if self._configuration.pubsub["include_metrics"] and Capability.METRIC_COLLECTION in request.capabilities:
                by_name = {item.native_resource_id.rsplit("/", 1)[-1]: item for item in resources}
                now = datetime.now(timezone.utc)
                interval = {
                    "start_time": now - timedelta(seconds=self._configuration.monitoring["lookback_seconds"]),
                    "end_time": now,
                }
                try:
                    for metric_name in sorted(ALLOWED_METRICS):
                        series_set = collect_metric_series(
                            monitoring,
                            project.project_id,
                            metric_name,
                            interval,
                            self._configuration.monitoring["alignment_period_seconds"],
                            self._configuration.limits["maximum_metric_series"],
                        )
                        for series in series_set:
                            labels = dict(getattr(getattr(series, "resource", None), "labels", {}) or {})
                            resource = by_name.get(labels.get("subscription_id") or labels.get("topic_id"))
                            if resource is None:
                                continue
                            points = list(getattr(series, "points", ()) or ())
                            value = point_value(points[0]) if points else None
                            kind = str(getattr(series, "metric_kind", "GAUGE")).rsplit(".", 1)[-1]
                            region = labels.get("region", labels.get("location", ""))
                            yield metric(
                                resource,
                                metric_name,
                                value,
                                kind,
                                self._configuration.monitoring["alignment_period_seconds"],
                                region=region,
                                scope="regional" if metric_name in REGIONAL_BACKLOG_METRICS else "global",
                            )
                except Exception:
                    yield PartialFailure(
                        "metric_collection",
                        "monitoring_api_unavailable",
                        "Cloud Monitoring evidence is unavailable",
                        True,
                    )
