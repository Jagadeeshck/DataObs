from __future__ import annotations

import argparse
import json
import signal
import time
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone

import yaml  # type: ignore[import-untyped]

from integrations.databases.postgres.connector import PostgresConnector
from integrations.databases.postgres.models import PostgresConnectionConfig
from packages.agent_sdk.models import BaseRequest, ConnectorIdentity, ResultMetadata, ScanTask
from packages.agent_sdk.registry import ConnectorRegistry
from services.scanner_worker.worker import ScannerWorker

RUNNING = True


def _stop(*_):
    global RUNNING
    RUNNING = False


def load_config(path):
    if not path:
        return {}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _json(obj):
    if is_dataclass(obj):
        return asdict(obj)
    if hasattr(obj, "__dict__"):
        return obj.__dict__
    return str(obj)


def pg_config(cfg: dict) -> PostgresConnectionConfig | None:
    pg = cfg.get("postgres", {})
    if not pg.get("host"):
        return None
    return PostgresConnectionConfig(
        host=pg["host"],
        port=int(pg.get("port", 5432)),
        database=pg["database"],
        username=pg["username"],
        password_ref=pg["password_ref"],
        sslmode=pg.get("sslmode", "prefer"),
        sslrootcert=pg.get("sslrootcert"),
        connect_timeout=int(pg.get("connect_timeout", 5)),
        statement_timeout_ms=int(pg.get("statement_timeout_ms", 5000)),
        application_name=pg.get("application_name", "dataobs_scanner"),
    )


def make_connector(cfg: dict, task_context: dict | None = None):
    scanner_id = cfg.get("scanner_id", "local-postgres-scanner")
    return PostgresConnector(
        pg_config(cfg),
        task_context=task_context,
        scanner_id=scanner_id,
        allow_schemas=cfg.get("allow_schemas"),
        deny_schemas=cfg.get("deny_schemas"),
        allow_tables=cfg.get("allow_tables"),
        deny_tables=cfg.get("deny_tables"),
    )


def _request(cfg: dict, operation: str, options: dict | None = None) -> BaseRequest:
    md = ResultMetadata(
        cfg.get("tenant_id", "demo-tenant"),
        cfg.get("environment", "demo"),
        cfg.get("integration_id", cfg.get("source_id", "postgres-demo")),
        ConnectorIdentity("postgres", "0.2.0", "postgres"),
        cfg.get("execution_id", f"exec-{int(time.time())}"),
        cfg.get("task_id", f"task-{operation}"),
        datetime.now(timezone.utc),
        None,
        "postgres",
        cfg.get("asset", "*"),
        correlation_trace_id=cfg.get("trace_id"),
    )
    return BaseRequest(md, options or cfg.get("options", {}))


def registry(cfg: dict):
    r = ConnectorRegistry()
    r.register("postgres", lambda: make_connector(cfg))
    return r


def main(argv=None):
    p = argparse.ArgumentParser(prog="dataobs-scanner")
    p.add_argument("--config", default="config/postgres-scanner.example.yaml")
    sub = p.add_subparsers(dest="cmd", required=True)
    for c in ["run", "test-connection", "discover", "scan-once", "print-capabilities"]:
        sp = sub.add_parser(c)
        sp.add_argument("--operation", default=None)
    a = p.parse_args(argv)
    cfg = load_config(a.config)
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    if a.cmd == "print-capabilities":
        conn = make_connector(cfg)
        print(json.dumps(conn.capabilities(), default=_json))
        return 0
    if a.cmd == "test-connection":
        conn = make_connector(cfg)
        res = conn.test_connection()
        print(json.dumps(res, default=_json))
        conn.close()
        return 0 if res.ok else 2
    if a.cmd == "discover":
        conn = make_connector(cfg)
        res = conn.discover(_request(cfg, "discover"))
        print(json.dumps(res, default=_json))
        conn.close()
        return 0
    if a.cmd == "scan-once":
        op = a.operation or cfg.get("operation", "discover")
        task = ScanTask(
            cfg.get("task_id", f"task-{op}"),
            cfg.get("tenant_id", "demo-tenant"),
            cfg.get("environment", "demo"),
            cfg.get("integration_id", "postgres-demo"),
            "postgres",
            op,
            "postgres",
            options=cfg.get("options", {}),
            timeout_seconds=int(cfg.get("timeout_seconds", 30)),
        )
        ex = ScannerWorker(registry(cfg), worker_id=cfg.get("scanner_id")).run(task)
        print(json.dumps(ex, default=_json))
        return 0 if ex.error is None else 3
    while RUNNING:
        print(
            json.dumps(
                {
                    "event": "heartbeat",
                    "scanner_id": cfg.get("scanner_id", "local-postgres-scanner"),
                    "observed_at": datetime.now(timezone.utc).isoformat(),
                }
            ),
            flush=True,
        )
        time.sleep(int(cfg.get("heartbeat_interval_seconds", 10)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
