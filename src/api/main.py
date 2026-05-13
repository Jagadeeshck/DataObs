"""
DataObs API Server

Lightweight HTTP API backed by Elasticsearch (or in-memory for local dev).

Authentication
--------------
Set API_TOKEN env var.  All requests must carry:

    Authorization: Bearer <token>

If API_TOKEN is not set the server starts with a warning and allows
unauthenticated access (local dev only).

Environment variables
---------------------
API_TOKEN               Shared bearer token for all clients
API_HOST                Bind host (default: 0.0.0.0)
API_PORT                Bind port (default: 8080)
ELASTICSEARCH_URL       ES endpoint (default: http://localhost:9200)
ELASTICSEARCH_USER      ES username (default: elastic)
ELASTICSEARCH_PASSWORD  ES password (default: "")
DATAOBS_STORE_BACKEND   "elasticsearch" | "memory" (default: memory)
DATAOBS_TENANT_ID       Tenant ID for index partitioning (default: default)
LOG_LEVEL               Python log level (default: INFO)

Endpoints
---------
GET  /health                         → 200 {"status": "ok"}
GET  /rules                          → list all rules
POST /rules                          → add a rule (JSON body)
DELETE /rules/<rule_id>              → delete a rule
GET  /lineage/nodes                  → all lineage nodes
GET  /lineage/edges                  → all lineage edges
GET  /lineage/impact/<node_id>       → downstream BFS impact
GET  /quality/results                → list quality results
POST /quality/results                → save a quality result
GET  /strategy/enterprise-backlog    → prioritised enterprise capability backlog
"""
from __future__ import annotations

import json
import logging
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict

from elasticsearch import Elasticsearch

from src.api.store import LineageStore, RuleStore, get_store
from src.core.enterprise_blueprint import enterprise_backlog

logger = logging.getLogger(__name__)


def _active_store() -> Any:
    """Return the unified store, falling back to legacy test/dev globals."""
    return _store or _rule_store or _lineage_store


def _rules_store() -> Any:
    """Return the store that owns quality rules."""
    return _store or _rule_store


def _lineage_source() -> Any:
    """Return the store that owns lineage queries."""
    return _lineage_store or _store


# ---------------------------------------------------------------------------
# Globals (set once in main(), read by handler)
# ---------------------------------------------------------------------------
_store:        Any = None         # unified store (ES or in-memory)
_rule_store:   RuleStore | None   = None  # kept for legacy compat
_lineage_store: LineageStore | None = None
_api_token:    str | None = None


# ---------------------------------------------------------------------------
# Auth helper
# ---------------------------------------------------------------------------

def _is_authorised(handler: BaseHTTPRequestHandler) -> bool:
    if _api_token is None:
        return True
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
    server_version = "DataObs/1.0"
    sys_version = ""

    def log_message(self, fmt: str, *args) -> None:  # type: ignore[override]
        logger.info("%s — %s", self.address_string(), fmt % args)

    def _guard(self) -> bool:
        if not _is_authorised(self):
            _send_401(self)
            return False
        return True

    # ── GET ───────────────────────────────────────────────────────────────

    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?")[0].rstrip("/")

        if path == "/health":
            _send_json(self, 200, {
                "status": "ok",
                "service": "dataobs-api",
                "store_backend": os.getenv("DATAOBS_STORE_BACKEND", "memory"),
            })
            return

        if not self._guard():
            return

        if path == "/rules":
            rules = _rules_store().get_all_rules()
            _send_json(self, 200, {"rules": rules, "count": len(rules)})

        elif path == "/lineage/nodes":
            nodes = _lineage_source().get_all_nodes()
            _send_json(self, 200, {"nodes": nodes, "count": len(nodes)})

        elif path == "/lineage/edges":
            edges = _lineage_source().get_all_edges()
            _send_json(self, 200, {"edges": edges, "count": len(edges)})

        elif path.startswith("/lineage/impact/"):
            node_id = path[len("/lineage/impact/"):]
            if not node_id:
                _send_json(self, 400, {"error": "node_id is required"})
                return
            src = _lineage_source()
            affected = src.get_downstream_impact(node_id)
            _send_json(self, 200, {"root_node": node_id, "affected": affected, "count": len(affected)})

        elif path == "/quality/results":
            results = _active_store().list_quality_results()
            _send_json(self, 200, {"results": results, "count": len(results)})

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
                rule_id = _rules_store().add_rule(rule)
                _send_json(self, 201, {"rule_id": rule_id, "status": "created"})
            except (json.JSONDecodeError, ValueError) as exc:
                _send_json(self, 400, {"error": f"Invalid JSON body: {exc}"})

        elif path == "/quality/results":
            try:
                result = _read_json_body(self)
                doc_id = _active_store().save_quality_result(result)
                _send_json(self, 201, {"id": doc_id, "status": "created"})
            except (json.JSONDecodeError, ValueError) as exc:
                _send_json(self, 400, {"error": f"Invalid JSON body: {exc}"})

        else:
            _send_404(self)

    # ── DELETE ────────────────────────────────────────────────────────────

    def do_DELETE(self) -> None:  # noqa: N802
        path = self.path.split("?")[0].rstrip("/")

        if not self._guard():
            return

        if path.startswith("/rules/"):
            rule_id = path[len("/rules/"):]
            if not rule_id:
                _send_json(self, 400, {"error": "rule_id is required"})
                return
            deleted = _rules_store().delete_rule(rule_id)
            if deleted:
                _send_json(self, 200, {"rule_id": rule_id, "status": "deleted"})
            else:
                _send_json(self, 404, {"error": f"Rule '{rule_id}' not found"})
        else:
            _send_404(self)

    def do_PUT(self) -> None:  # noqa: N802
        _send_405(self)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _make_es_client() -> Elasticsearch:
    url      = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
    user     = os.getenv("ELASTICSEARCH_USER", "elastic")
    password = os.getenv("ELASTICSEARCH_PASSWORD", "")
    return Elasticsearch([url], basic_auth=(user, password), request_timeout=30)


def main() -> None:
    global _store, _rule_store, _lineage_store, _api_token

    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    )

    host      = os.getenv("API_HOST", "0.0.0.0")
    port      = int(os.getenv("API_PORT", "8080"))
    tenant_id = os.getenv("DATAOBS_TENANT_ID", "default")

    _api_token = os.getenv("API_TOKEN") or None
    if _api_token is None:
        logger.warning(
            "API_TOKEN is not set — running in unauthenticated dev mode. "
            "Set API_TOKEN in production."
        )
    else:
        logger.info("Bearer token authentication enabled.")

    es = _make_es_client()

    # Initialise the unified store (ES or in-memory)
    _store = get_store(es_client=es, tenant_id=tenant_id)

    # Keep legacy ES-backed stores wired for lineage BFS (they use node/edge indices
    # that LineageTracker writes directly — distinct from the unified store indices).
    _rule_store    = RuleStore(es)
    _lineage_store = LineageStore(es)

    server = ThreadingHTTPServer((host, port), DataObsHandler)
    logger.info(
        "DataObs API listening on http://%s:%d (store_backend=%s, tenant=%s)",
        host, port, os.getenv("DATAOBS_STORE_BACKEND", "memory"), tenant_id,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down API server …")
        server.shutdown()


if __name__ == "__main__":
    main()
