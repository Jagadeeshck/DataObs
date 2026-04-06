"""Lightweight HTTP API for DataObs rule and lineage management.

This module intentionally avoids external web framework dependencies, so it can run
in minimal environments. It exposes JSON endpoints for core management operations.
"""

from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from src.core.enterprise_blueprint import enterprise_backlog

from .store import LineageStore, RuleStore

RULES = RuleStore()
LINEAGE = LineageStore()


class DataObsHandler(BaseHTTPRequestHandler):
    server_version = "DataObsAPI/0.1"

    def _read_json(self) -> dict:
        content_length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(content_length).decode("utf-8") if content_length else "{}"
        return json.loads(raw or "{}")

    def _send(self, status: HTTPStatus, payload: dict | list) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/health":
            return self._send(HTTPStatus.OK, {"status": "ok", "service": "dataobs-api"})

        if path == "/rules":
            return self._send(HTTPStatus.OK, {"items": RULES.list_rules()})

        if path == "/lineage/nodes":
            return self._send(HTTPStatus.OK, {"items": LINEAGE.list_nodes()})

        if path == "/lineage/edges":
            return self._send(HTTPStatus.OK, {"items": LINEAGE.list_edges()})

        if path.startswith("/lineage/impact/"):
            node_id = path.split("/lineage/impact/", 1)[1]
            qs = parse_qs(parsed.query)
            depth = int(qs.get("depth", ["5"])[0])
            impacted = LINEAGE.downstream(node_id, depth=depth)
            return self._send(HTTPStatus.OK, {"root_node_id": node_id, "downstream": impacted})

        if path == "/strategy/enterprise-backlog":
            qs = parse_qs(parsed.query)
            implemented_param = qs.get("implemented", [""])[0]
            implemented = [item for item in implemented_param.split(",") if item]
            backlog = enterprise_backlog(implemented)
            return self._send(
                HTTPStatus.OK,
                {
                    "implemented": implemented,
                    "recommended_backlog": backlog,
                    "summary": {
                        "total_capabilities": len(backlog) + len(implemented),
                        "implemented_count": len(implemented),
                        "remaining_count": len(backlog),
                    },
                },
            )

        return self._send(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def do_POST(self):  # noqa: N802
        path = urlparse(self.path).path

        if path.startswith("/rules/"):
            rule_id = path.split("/rules/", 1)[1]
            record = RULES.upsert_rule(rule_id, self._read_json())
            return self._send(HTTPStatus.CREATED, record)

        if path.startswith("/lineage/nodes/"):
            node_id = path.split("/lineage/nodes/", 1)[1]
            record = LINEAGE.upsert_node(node_id, self._read_json())
            return self._send(HTTPStatus.CREATED, record)

        if path == "/lineage/edges":
            payload = self._read_json()
            if not payload.get("source_node_id") or not payload.get("target_node_id"):
                return self._send(HTTPStatus.BAD_REQUEST, {"error": "source_node_id and target_node_id are required"})
            record = LINEAGE.add_edge(payload)
            return self._send(HTTPStatus.CREATED, record)

        return self._send(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def do_DELETE(self):  # noqa: N802
        path = urlparse(self.path).path
        if path.startswith("/rules/"):
            rule_id = path.split("/rules/", 1)[1]
            if RULES.delete_rule(rule_id):
                return self._send(HTTPStatus.OK, {"deleted": rule_id})
            return self._send(HTTPStatus.NOT_FOUND, {"error": "rule_not_found"})

        return self._send(HTTPStatus.NOT_FOUND, {"error": "not_found"})


def run(host: str = "0.0.0.0", port: int = 8080) -> None:
    server = ThreadingHTTPServer((host, port), DataObsHandler)
    print(f"DataObs API listening on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
