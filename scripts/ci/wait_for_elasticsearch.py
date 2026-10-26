#!/usr/bin/env python3
"""Wait for a usable Elasticsearch cluster, failing closed on timeout."""

from __future__ import annotations

import argparse
import base64
import json
import ssl
import sys
import time
import urllib.error
import urllib.request

READY = {"yellow", "green"}


def request_json(endpoint: str, headers: dict[str, str], context: ssl.SSLContext | None, timeout: float):
    """Return one JSON response while respecting the caller's remaining deadline."""
    with urllib.request.urlopen(
        urllib.request.Request(endpoint, headers=headers), timeout=max(0.01, min(10, timeout)), context=context
    ) as response:
        return json.load(response)


def wait(
    url: str, timeout: float, interval: float, username: str | None, password: str | None, verify_tls: bool
) -> bool:
    deadline = time.monotonic() + timeout
    base_url = url.rstrip("/")
    health_endpoint = f"{base_url}/_cluster/health?wait_for_status=yellow&timeout=5s"
    indices_endpoint = f"{base_url}/_cat/indices?format=json"
    headers = {"Accept": "application/json"}
    if username is not None:
        token = base64.b64encode(f"{username}:{password or ''}".encode()).decode()
        headers["Authorization"] = f"Basic {token}"
    context = None if verify_tls else ssl._create_unverified_context()  # noqa: S323 - explicit CI option
    attempt = 0
    last_error = "no response"
    while time.monotonic() < deadline:
        attempt += 1
        try:
            remaining = deadline - time.monotonic()
            payload = request_json(health_endpoint, headers, context, remaining)
            status = payload.get("status")
            if status in READY and not payload.get("timed_out", False):
                # Exercise an indices API used during application startup. A healthy
                # service-container probe can precede transient transport resets.
                indices = request_json(indices_endpoint, headers, context, deadline - time.monotonic())
                if not isinstance(indices, list):
                    raise ValueError("Elasticsearch indices API did not return a JSON list")
                print(f"Elasticsearch ready: status={status}, attempts={attempt}")
                return True
            last_error = f"cluster status={status!r}, timed_out={payload.get('timed_out')!r}"
        except (OSError, ValueError, urllib.error.URLError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
        print(f"Elasticsearch not ready (attempt {attempt}): {last_error}", file=sys.stderr)
        time.sleep(min(interval, max(0, deadline - time.monotonic())))
    print(f"ERROR: Elasticsearch readiness timed out after {timeout:g}s: {last_error}", file=sys.stderr)
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:9200")
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("--interval", type=float, default=2)
    parser.add_argument("--username")
    parser.add_argument("--password")
    parser.add_argument("--insecure", action="store_true", help="Disable TLS certificate verification")
    args = parser.parse_args()
    if args.timeout <= 0 or args.interval <= 0:
        parser.error("timeout and interval must be positive")
    return 0 if wait(args.url, args.timeout, args.interval, args.username, args.password, not args.insecure) else 1


if __name__ == "__main__":
    raise SystemExit(main())
