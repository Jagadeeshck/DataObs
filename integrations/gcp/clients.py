from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from .authentication import create_credentials
from .errors import error

PUBLISHER_ALLOWED = frozenset({"list_topics", "get_topic"})
SUBSCRIBER_ALLOWED = frozenset({"list_subscriptions", "get_subscription"})
MONITORING_ALLOWED = frozenset({"list_time_series"})


class ReadOnlyClient:
    def __init__(self, client, allowed: frozenset[str]):
        self._client = client
        self._allowed = allowed

    def invoke(self, operation: str, *args, **kwargs):
        if operation not in self._allowed:
            raise error("access_denied", "read_only_boundary")
        return getattr(self._client, operation)(*args, **kwargs)


class GoogleCloudClientFactory:
    def create(self, configuration):
        try:
            from google.cloud import monitoring_v3, pubsub_v1
        except ImportError as exc:
            raise error("dependency_unavailable", "dependencies") from exc
        credentials = create_credentials(configuration.authentication)
        return (
            ReadOnlyClient(pubsub_v1.PublisherClient(credentials=credentials), PUBLISHER_ALLOWED),
            ReadOnlyClient(pubsub_v1.SubscriberClient(credentials=credentials), SUBSCRIBER_ALLOWED),
            ReadOnlyClient(monitoring_v3.MetricServiceClient(credentials=credentials), MONITORING_ALLOWED),
        )

    @staticmethod
    def versions() -> dict[str, str]:
        result = {}
        for package in ("google-cloud-pubsub", "google-cloud-monitoring", "google-auth", "google-api-core"):
            try:
                result[package] = version(package)
            except PackageNotFoundError:
                result[package] = "unavailable"
        return result
