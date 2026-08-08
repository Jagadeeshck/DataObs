from __future__ import annotations

from packages.collectors.sdk import (
    Capability,
    CollectionMode,
    ConnectionTestResult,
    PartialFailure,
    ProviderCapabilities,
    ValidationIssue,
    ValidationResult,
)
from packages.collectors.sdk.errors import IntegrationError

from .clients import BigQueryClientFactory
from .collectors import datasets, job_timeline, jobs, models, projects, reservations, routines, storage, tables
from .configuration import parse_configuration
from .errors import map_google_error
from .evidence import LIMITATIONS


class BigQueryWarehouseProvider:
    provider_type = "bigquery"
    provider_version = "1"

    def __init__(self, client_factory=None):
        self._factory = client_factory or BigQueryClientFactory()
        self._configuration = None

    def capabilities(self):
        return ProviderCapabilities(
            frozenset(
                {
                    Capability.RESOURCE_DISCOVERY,
                    Capability.METADATA_COLLECTION,
                    Capability.METRIC_COLLECTION,
                    Capability.QUERY_HISTORY,
                    Capability.SCHEMA_DISCOVERY,
                    Capability.HEALTH_CHECK,
                    Capability.INCREMENTAL_COLLECTION,
                }
            ),
            frozenset(
                {
                    Capability.LOG_COLLECTION,
                    Capability.LINEAGE_COLLECTION,
                    Capability.COST_COLLECTION,
                    Capability.EVENT_DRIVEN_COLLECTION,
                }
            ),
            (
                "roles/bigquery.metadataViewer",
                "bigquery.jobs.create when fixed metadata queries are enabled",
                "roles/bigquery.resourceViewer for project jobs/reservations",
            ),
            frozenset({CollectionMode.SCHEDULED, CollectionMode.ON_DEMAND}),
            (
                "google-cloud-bigquery>=3.25,<4",
                "google-cloud-bigquery-reservation>=1.13,<2",
                "google-auth>=2.35,<3",
                "google-api-core>=2.20,<3",
            ),
            LIMITATIONS,
        )

    async def validate_configuration(self, context, configuration):
        try:
            self._configuration = parse_configuration(configuration)
            return ValidationResult(True)
        except IntegrationError as exc:
            return ValidationResult(
                False, (ValidationIssue(str(exc.code), "provider", "BigQuery configuration is invalid"),)
            )

    async def test_connection(self, context, configuration):
        client = None
        try:
            cfg = parse_configuration(configuration)
            client = self._factory.create(cfg)
            next(iter(projects.collect(context, cfg, self._factory.versions())))
            return ConnectionTestResult(True, 0)
        except Exception as exc:
            safe = exc if isinstance(exc, IntegrationError) else map_google_error(exc)
            return ConnectionTestResult(False, error_code=str(safe.code), message="BigQuery connection test failed")
        finally:
            if client:
                self._factory.close(client)

    async def discover(self, context, request):
        async for item in self.collect(context, request):
            if not isinstance(item, PartialFailure):
                yield item

    async def collect(self, context, request):
        self.capabilities().require(request.capabilities)
        cfg = self._configuration
        if cfg is None:
            raise RuntimeError("configuration must be validated before collection")
        client = self._factory.create(cfg)
        try:
            for item in projects.collect(context, cfg, self._factory.versions()):
                yield item
            for project in cfg.projects:
                try:
                    ds = list(datasets.collect(client, context, cfg, project))
                except Exception as exc:
                    safe = exc if isinstance(exc, IntegrationError) else map_google_error(exc)
                    yield PartialFailure(
                        "metadata_collection", str(safe.code), "datasets: collection unavailable", safe.retryable
                    )
                    continue
                for d in ds:
                    yield d
                    raw = type("Dataset", (), {"dataset_id": d.native_resource_id, "location": d.region})()
                    for family, fn, enabled in (
                        ("tables", tables.collect, cfg.metadata.get("include_tables", True)),
                        ("models", models.collect, cfg.metadata.get("include_models", True)),
                        ("routines", routines.collect, cfg.metadata.get("include_routines", True)),
                    ):
                        if not enabled:
                            continue
                        try:
                            for item in fn(client, context, cfg, project, raw):
                                yield item
                        except Exception as exc:
                            safe = exc if isinstance(exc, IntegrationError) else map_google_error(exc)
                            yield PartialFailure(
                                "metadata_collection",
                                str(safe.code),
                                f"{family}: collection unavailable",
                                safe.retryable,
                            )
                for location in project.locations:
                    selected = []
                    if cfg.jobs.get("enabled", True):
                        selected.append(("jobs", jobs.collect))
                    if cfg.jobs.get("include_timeline_aggregation", False):
                        selected.append(("job_timeline", job_timeline.collect))
                    if cfg.storage.get("enabled", True):
                        selected.append(("storage", storage.collect))
                    for family, fn in selected:
                        try:
                            for item in fn(client, context, cfg, project, location, family):
                                yield item
                        except Exception as exc:
                            safe = exc if isinstance(exc, IntegrationError) else map_google_error(exc)
                            yield PartialFailure(
                                "query_history" if family != "storage" else "metric_collection",
                                str(safe.code),
                                f"{family}: collection unavailable",
                                safe.retryable,
                            )
            if cfg.reservations.get("enabled", False):
                rclient = None
                try:
                    rclient = self._factory.create_reservation(cfg)
                    admin = cfg.reservations["administration_project"]
                    for location in cfg.reservations.get("locations", ()):
                        try:
                            for item in reservations.collect(rclient, context, cfg, admin, location):
                                yield item
                        except Exception as exc:
                            safe = exc if isinstance(exc, IntegrationError) else map_google_error(exc)
                            yield PartialFailure(
                                "metric_collection",
                                str(safe.code),
                                "reservations: collection unavailable",
                                safe.retryable,
                            )
                finally:
                    if rclient:
                        self._factory.close(rclient)
        finally:
            self._factory.close(client)
