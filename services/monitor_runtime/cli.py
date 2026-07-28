"""Production composition root for the durable monitor runtime."""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
from pathlib import Path
from time import monotonic

from elasticsearch import Elasticsearch

from packages.elastic_store.registry import status as migration_status
from services.monitor_runtime.service import MonitorRuntime
from services.monitor_runtime.worker import MonitorWorker
from services.monitoring.as_code.parser import parse
from services.monitoring.as_code.planner import plan
from services.monitoring.capabilities import CAPABILITIES
from services.monitoring.elasticsearch_repository import ElasticsearchMonitorRepository
from services.monitoring.providers.postgres_executor import PostgresAggregateExecutor
from services.monitoring.providers.postgres_monitor import PostgresMonitorProvider
from services.monitoring.providers.registry import ProviderRegistry
from src.config.settings import load_settings


def compose() -> MonitorRuntime:
    settings = load_settings()
    if not settings.elasticsearch.url:
        raise RuntimeError("ELASTICSEARCH_URL is required")
    auth = (settings.elasticsearch.user, settings.elasticsearch.password) if settings.elasticsearch.user else None
    client = Elasticsearch(
        settings.elasticsearch.url,
        basic_auth=auth,
        api_key=settings.elasticsearch.api_key,
        verify_certs=settings.elasticsearch.verify_tls,
        request_timeout=10,
    )
    if not client.ping():
        raise RuntimeError("Elasticsearch is unavailable")
    state = migration_status(client)
    if state.get("missing") or state.get("checksum_mismatch"):
        raise RuntimeError("required Elasticsearch migrations are not applied")
    repository = ElasticsearchMonitorRepository(client)
    repository.readiness()

    registry = ProviderRegistry()
    dsn = os.getenv("DATAOBS_MONITOR_POSTGRES_DSN")
    allowed_raw = json.loads(os.getenv("DATAOBS_MONITOR_POSTGRES_ALLOWLIST", "{}"))
    if dsn:
        import psycopg2

        executor = PostgresAggregateExecutor(
            lambda: psycopg2.connect(
                dsn, connect_timeout=5, sslmode=os.getenv("DATAOBS_MONITOR_POSTGRES_SSLMODE", "require")
            ),
            allowed_relations={key: set(value) for key, value in allowed_raw.items()},
        )
        for monitor_type in CAPABILITIES:
            registry.register(monitor_type, PostgresMonitorProvider(executor, monitor_type))
    if not registry.ready:
        raise RuntimeError("no production observation provider is configured")
    worker = MonitorWorker(
        repository,
        registry,
        owner=os.getenv("DATAOBS_RUNTIME_ID", socket.gethostname()),
        lease_seconds=int(os.getenv("DATAOBS_MONITOR_LEASE_SECONDS", "30")),
    )
    return MonitorRuntime(
        repository,
        worker,
        tenant_id=os.environ["DATAOBS_TENANT_ID"],
        environment=os.getenv("DATAOBS_ENVIRONMENT", "default"),
        concurrency=int(os.getenv("DATAOBS_MONITOR_CONCURRENCY", "4")),
        batch_size=int(os.getenv("DATAOBS_MONITOR_BATCH_SIZE", "100")),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["run", "once", "health", "reconcile-definitions"])
    parser.add_argument("--file", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    started = monotonic()
    try:
        runtime = compose()
        if args.command == "run":
            runtime.run(float(os.getenv("DATAOBS_MONITOR_POLL_SECONDS", "5")))
            return 0
        if args.command == "once":
            summary = runtime.once()
            summary["duration_ms"] = round((monotonic() - started) * 1000)
            print(json.dumps(summary, sort_keys=True))
            return 0
        if args.command == "health":
            print(
                json.dumps(
                    {
                        "service": "monitor-runtime",
                        **runtime.repo.readiness(),
                        "providers_ready": runtime.worker.providers.ready,
                    }
                )
            )
            return 0
        if args.file is None:
            raise ValueError("--file is required for reconcile-definitions")
        desired = parse(args.file.read_text(encoding="utf-8"))
        current = runtime.repo.list_monitors(runtime.tenant_id, runtime.environment, limit=500)
        actions = plan(desired, current)
        # Applying remains OCC-protected by the canonical as-code applier. Never imply a plan was applied.
        if args.apply:
            raise ValueError("use `dataobs quality apply` for an OCC-protected apply")
        print(json.dumps({"mode": "plan", "actions": actions}, sort_keys=True))
        return 0
    except Exception as exc:
        print(
            json.dumps(
                {
                    "service": "monitor-runtime",
                    "live": True,
                    "ready": False,
                    "error": type(exc).__name__,
                    "reason": str(exc),
                }
            ),
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
