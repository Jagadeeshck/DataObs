#!/usr/bin/env python3
"""Fail closed when the live FastAPI registry drifts from the route policy."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.routing import APIRoute  # noqa: E402

from src.api.app import create_app  # noqa: E402
from src.security.route_policy import PUBLIC_ROUTES, permission_for_route  # noqa: E402


def inspect_routes() -> dict[str, object]:
    registered: list[dict[str, str]] = []
    unexpectedly_public: list[str] = []
    uncovered: list[str] = []
    seen: set[tuple[str, str]] = set()
    for route in create_app().routes:
        if not isinstance(route, APIRoute) or not route.path.startswith("/api/v1"):
            continue
        for method in sorted(route.methods - {"HEAD", "OPTIONS"}):
            key = (method, route.path)
            seen.add(key)
            public = key in PUBLIC_ROUTES
            try:
                perm = permission_for_route(method, route.path)
                permission = "public" if perm is None else perm.value
            except LookupError:
                uncovered.append(f"{method} {route.path}: route has no explicit permission policy")
                registered.append({"method": method, "path": route.path, "permission": "unknown"})
                continue
            dependencies = {getattr(item.call, "__name__", "") for item in route.dependant.dependencies}
            has_auth = "require_auth" in dependencies
            if public and has_auth:
                unexpectedly_public.append(f"{method} {route.path}: allowlisted route requires authentication")
            if not public and perm is not None and not has_auth:
                uncovered.append(f"{method} {route.path}: protected route lacks require_auth")
            registered.append({"method": method, "path": route.path, "permission": permission})
    stale = [f"{method} {path}" for method, path in sorted(PUBLIC_ROUTES - seen)]
    return {
        "schema_version": "1",
        "status": "pass" if not (uncovered or stale or unexpectedly_public) else "fail",
        "routes": sorted(registered, key=lambda item: (item["path"], item["method"])),
        "uncovered_routes": uncovered,
        "stale_public_entries": stale,
        "unexpectedly_public_routes": unexpectedly_public,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = inspect_routes()
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
