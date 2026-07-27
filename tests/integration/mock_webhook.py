"""Stateful, redacting webhook receiver used only by the integration stack."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

REQUESTS: list[dict] = []


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return

    def _reply(self, status: int, body: object, content_type: str = "application/json") -> None:
        encoded = body.encode() if isinstance(body, str) else json.dumps(body).encode()
        self.send_response(status)
        self.send_header("content-type", content_type)
        self.send_header("content-length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self) -> None:
        if self.path == "/health":
            self._reply(200, {"status": "ok"})
        elif self.path == "/_requests":
            self._reply(200, {"requests": REQUESTS})
        else:
            self._reply(404, {"error": "not_found"})

    def do_DELETE(self) -> None:
        if self.path == "/_requests":
            REQUESTS.clear()
            self._reply(204, "")
        else:
            self._reply(404, {"error": "not_found"})

    def do_POST(self) -> None:
        parsed = urlsplit(self.path)
        if parsed.path not in {"/slack", "/pagerduty", "/servicenow/api/now/table/incident"}:
            self._reply(404, {"error": "not_found"})
            return
        length = int(self.headers.get("content-length", "0"))
        body = json.loads(self.rfile.read(length) or b"{}")
        if "routing_key" in body:
            body["routing_key"] = "[REDACTED]"
        REQUESTS.append(
            {
                "method": "POST",
                "path": parsed.path,
                "headers": {"content-type": self.headers.get("content-type")},
                "body": body,
            }
        )
        requested_status = int(parse_qs(parsed.query).get("status", ["0"])[0])
        if requested_status:
            self._reply(requested_status, {"error": "configured channel failure"})
        elif parsed.path == "/slack":
            self._reply(200, "ok", "text/plain")
        elif parsed.path == "/pagerduty":
            self._reply(202, {"status": "success", "dedup_key": body.get("dedup_key")})
        else:
            self._reply(201, {"result": {"number": "INC001"}})


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
