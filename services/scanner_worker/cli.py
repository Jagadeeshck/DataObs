from __future__ import annotations

import argparse
import json
import signal
import time
from pathlib import Path

import yaml  # type: ignore[import-untyped]

from integrations.databases.postgres.connector import PostgresConnector
from packages.agent_sdk.registry import ConnectorRegistry

RUNNING = True


def _stop(*_):
    global RUNNING
    RUNNING = False


def load_config(path):
    if not path:
        return {}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def registry():
    r = ConnectorRegistry()
    r.register("postgres", lambda: PostgresConnector())
    return r


def main(argv=None):
    p = argparse.ArgumentParser(prog="dataobs-scanner")
    p.add_argument("--config", default="config/postgres-scanner.example.yaml")
    sub = p.add_subparsers(dest="cmd", required=True)
    for c in ["run", "test-connection", "discover", "scan-once", "print-capabilities"]:
        sub.add_parser(c)
    a = p.parse_args(argv)
    cfg = load_config(a.config)
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    conn = PostgresConnector(dsn=cfg.get("postgres", {}).get("dsn"), allow_schemas=cfg.get("allow_schemas"))
    if a.cmd == "print-capabilities":
        print(json.dumps(conn.capabilities().__dict__, default=str))
        return 0
    if a.cmd == "test-connection":
        print(json.dumps(conn.test_connection().__dict__, default=str))
        return 0
    if a.cmd in {"discover", "scan-once"}:
        print(json.dumps({"status": "ok", "operation": a.cmd, "raw_rows_persisted": False}))
        return 0
    while RUNNING:
        print(
            json.dumps({"event": "heartbeat", "scanner_id": cfg.get("scanner_id", "local-postgres-scanner")}),
            flush=True,
        )
        time.sleep(int(cfg.get("heartbeat_interval_seconds", 10)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
