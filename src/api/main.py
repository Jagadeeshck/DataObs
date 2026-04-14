"""
DataObs API Server

Lightweight HTTP API backed by Elasticsearch.  All state (rules, lineage)
is stored in ES — no in-memory store, so multiple replicas share data and
restarts are stateless.

Authentication
--------------
Set API_TOKEN env var.  All requests must carry:

    Authorization: Bearer <token>

If API_TOKEN is not set the server starts but logs a prominent warning and
allows unauthenticated access (useful for local dev only).

Environment variables
---------------------
API_TOKEN               Shared bearer token for all clients
API_HOST                Bind host (default: 0.0.0.0)
API_PORT                Bind port (default: 8080)
ELASTICSEARCH_URL       ES endpoint (default: http://localhost:9200)
ELASTICSEARCH_USER      ES username (default: elastic)
ELASTICSEARCH_PASSWORD  ES password (default: "")
LOG_LEVEL               Python log level (default: INFO)

Endpoints
---------
GET  /health                         → 200 {"status": "ok"}
GET  /rules                          → list all rules
POST /rules                          → add a rule (JSON body)
GET  /lineage/nodes                  → all lineage nodes
GET  /lineage/edges                  → all lineage edges
GET  /lineage/impact/<node_id>       → downstream BFS impact
GET  /strategy/enterprise-backlog    → prioritised enterprise capability backlog
"""
from __future__ import annotations

import json
import logging
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict

from elasticsearch import Elasticsearch

from src.api.store import LineageStore, RuleStore
from src.core.enterprise_blueprint import enterprise_backlog

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Globals (set once in main(), read by handler)
# ---------------------------------------------------------------------------
_rule_store: RuleStore | None = None
_lineage_store: LineageStore | None = None
_api_token: str | None = None  # None means auth disabled (dev mode)


# ---------------------------------------------------------------------------
# Auth helper
# ---------------------------------------------------------------------------

def _is_authorised(handler: BaseHTTPRequestHandler) -> bool:
    """Return True if the request carries a valid Bearer token, or if auth is disabled."""
    if _api_token is None:
        return True  # auth not configured — dev mode
    auth_header = handler.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return False
    return auth_header[len("Bearer "):].strip() == _api_token


# ---------------------------------------------------------------------------
# Response helpers
# ---------------------------------------------------------------------------

def _send_json(handler: BaseHTTPRequestHandler, status: int, body: Any) -> None:
    payload = json.dumps(body, default=str).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(payload)))
    handler.end_headers()
    handler.wfile.write(payload)


def _send_401(handler: BaseHTTPRequestHandler) -> None:
    handler.send_response(401)
    handler.send_header("WWW-Authenticate", 'Bearer realm="DataObs API"')
    handler.send_header("Content-Type", "application/json")
    handler.end_headers()
    handler.wfile.write(b'{"error": "Unauthorized - valid Bearer token required"}')


def _send_404(handler: BaseHTTPRequestHandler) -> None:
    _send_json(handler, 404, {"error": "Not found"})


def _send_405(handler: BaseHTTPRequestHandler) -> None:
    _send_json(handler, 405, {"error": "Method not allowed"})


def _read_json_body(handler: BaseHTTPRequestHandler) -> Dict[str, Any]:
    length = int(handler.headers.get("Content-Length", 0))
    if length == 0:
        return {}
    raw = handler.rfile.read(length)
    return json.loads(raw.decode("utf-8"))


# ---------------------------------------------------------------------------
# Request handler
# ---------------------------------------------------------------------------

class DataObsHandler(BaseHTTPRequestHandler):
    """Route HTTP requests to the appropriate store method."""

    server_version = "DataObs/1.0"
    sys_version = ""  # suppress Python version disclosure

    def log_message(self, fmt: str, *args) -> None:  # type: ignore[override]
        logger.info("%s — %s", self.address_string(), fmt % args)

    # ── Auth guard ────────────────────────────────────────────────────────

    def _guard(self) -> bool:
        """Return True if request is authorised; send 401 and return False otherwise."""
        if not _is_authorised(self):
            _send_401(self)
            return False
        return True

    # ── GET ───────────────────────────────────────────────────────────────

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?")[0].rstrip("/")

        # Health check — no auth required so load-balancers can probe freely
        if path == "/health":
            _send_json(self, 200, {"status": "ok", "service": "dataobs-api"})
            return

        if not self._guard():
            return

        if path == "/rules":
            rules = _rule_store.get_all_rules()
            _send_json(self, 200, {"rules": rules, "count": len(rules)})

        elif path == "/lineage/nodes":
            nodes = _lineage_store.get_all_nodes()
            _send_json(self, 200, {"nodes": nodes, "count": len(nodes)})

        elif path == "/lineage/edges":
            edges = _lineage_store.get_all_edges()
            _send_json(self, 200, {"edges": edges, "count": len(edges)})

        elif path.startswith("/lineage/impact/"):
            node_id = path[len("/lineage/impact/"):]
            if not node_id:
                _send_json(self, 400, {"error": "node_id is required"})
                return
            affected = _lineage_store.get_downstream_impact(node_id)
            _send_json(self, 200, {"root_node": node_id, "affected": affected, "count": len(affected)})

        elif path == "/strategy/enterprise-backlog":
            backlog = enterprise_backlog(implemented_keys=[])
            _send_json(self, 200, {"backlog": backlog})

        else:
            _send_404(self)

    # ── POST ──────────────────────────────────────────────────────────────

    def do_POST(self) -> None:  # noqa: N802
        path = self.path.split("?")[0].rstrip("/")

        if not self._guard():
            return

        if path == "/rules":
            try:
                rule = _read_json_body(self)
                rule_id = _rule_store.add_rule(rule)
                _send_json(self, 201, {"rule_id": rule_id, "status": "created"})
            except (json.JSONDecodeError, ValueError) as exc:
                _send_json(self, 400, {"error": f"Invalid JSON body: {exc}"})
        else:
            _send_404(self)

    # ── Unsupported methods ───────────────────────────────────────────────

    def do_PUT(self) -> None:   # noqa: N802
        _send_405(self)

    def do_DELETE(self) -> None:  # noqa: N802
        _send_405(self)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _make_es_client() -> Elasticsearch:
    url = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
    user = os.getenv("ELASTICSEARCH_USER", "elastic")
    password = os.getenv("ELASTICSEARCH_PASSWORD", "")
    return Elasticsearch(
        [url],
        basic_auth=(user, password),
        request_timeout=30,
    )


def main() -> None:
    global _rule_store, _lineage_store, _api_token

    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    )

    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8080"))

    _api_token = os.getenv("API_TOKEN") or None
    if _api_token is None:
        logger.warning(
            "API_TOKEN is not set — running in unauthenticated dev mode. "
            "Set API_TOKEN in production."
        )
    else:
        logger.info("Bearer token authentication enabled.")

    es = _make_es_client()
    _rule_store = RuleStore(es)
    _lineage_store = LineageStore(es)

    server = ThreadingHTTPServer((host, port), DataObsHandler)
    logger.info("DataObs API listening on http://%s:%d", host, port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down API server …")
        server.shutdown()


if __name__ == "__main__":
    main()
