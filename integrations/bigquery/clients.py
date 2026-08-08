from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from .authentication import create_credentials
from .errors import safe_error

ALLOWED = frozenset(
    {
        "list_datasets",
        "get_dataset",
        "list_tables",
        "get_table",
        "list_models",
        "get_model",
        "list_routines",
        "get_routine",
        "list_jobs",
        "fixed_query",
        "list_reservations",
        "get_reservation",
    }
)


class ReadOnlyClient:
    def __init__(self, client):
        self._client = client

    def invoke(self, operation, *args, **kwargs):
        if operation not in ALLOWED:
            raise safe_error("unsupported_feature")
        if operation == "fixed_query":
            return self._client.query(*args, **kwargs)
        return getattr(self._client, operation)(*args, **kwargs)


class BigQueryClientFactory:
    def create(self, cfg):
        try:
            from google.cloud import bigquery
        except ImportError as exc:
            raise safe_error("dependency_unavailable") from exc
        credentials = create_credentials(cfg.authentication)
        billing = cfg.query_execution.get("billing_project") or cfg.projects[0].project_id
        return ReadOnlyClient(
            bigquery.Client(project=billing, credentials=credentials, client_info=self._client_info())
        )

    def create_reservation(self, cfg):
        try:
            from google.cloud import bigquery_reservation_v1
        except ImportError as exc:
            raise safe_error("dependency_unavailable") from exc
        return ReadOnlyClient(
            bigquery_reservation_v1.ReservationServiceClient(credentials=create_credentials(cfg.authentication))
        )

    def _client_info(self):
        try:
            from google.api_core.client_info import ClientInfo

            return ClientInfo(user_agent="dataobs-bigquery-collector/1")
        except ImportError as exc:
            raise safe_error("dependency_unavailable") from exc

    def versions(self):
        out = {}
        for p in ("google-cloud-bigquery", "google-cloud-bigquery-reservation", "google-auth", "google-api-core"):
            try:
                out[p] = version(p)
            except PackageNotFoundError:
                out[p] = "unavailable"
        return out

    def close(self, client):
        raw = getattr(client, "_client", client)
        close = getattr(raw, "close", None)
        if close:
            close()
