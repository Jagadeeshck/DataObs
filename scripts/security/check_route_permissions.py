#!/usr/bin/env python3
"""Fail when a registered API route has no single explicit permission policy."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.api.app import create_app
from src.security.route_policy import PUBLIC_ROUTES, permission_for_route


def main() -> int:
    app = create_app()
    failures = []
    ignored = {"/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"}
    for route in app.routes:
        path = getattr(route, "path", "")
        if path in ignored:
            continue
        for method in sorted(getattr(route, "methods", set()) - {"OPTIONS"}):
            if (method, path) in PUBLIC_ROUTES:
                continue
            try:
                permission_for_route(method, path)
            except LookupError as exc:
                failures.append(str(exc))
    if failures:
        print("\n".join(failures))
        return 1
    print("all registered API routes have exactly one explicit permission policy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
