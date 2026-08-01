#!/usr/bin/env python3
"""Check the live FastAPI registry against the authoritative v1 route policy."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.api.app import create_app
from src.security.route_policy import PUBLIC_ROUTES, matching_rule, permission_for_route


def _has_auth_dependency(route: Any) -> bool:
    dependant = getattr(route, "dependant", None)
    return any(getattr(item.call, "__name__", "") == "require_auth" for item in getattr(dependant, "dependencies", ()))


def build_report() -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    for route in create_app().routes:
        path = getattr(route, "path", "")
        if not path.startswith("/api/v1"):
            continue
        for method in sorted((getattr(route, "methods", set()) or set()) - {"HEAD", "OPTIONS"}):
            key = (method, path)
            public = key in PUBLIC_ROUTES
            protected = _has_auth_dependency(route)
            row: dict[str, Any] = {"method": method, "path": path, "public": public, "protected": protected}
            if public:
                row["policy"] = "public"
                if protected:
                    errors.append(f"allowlisted public route unexpectedly requires authentication: {method} {path}")
            else:
                rule = matching_rule(method, path)
                if rule is None:
                    errors.append(f"uncovered route: {method} {path}")
                    row["policy"] = "missing"
                else:
                    row.update(policy=rule.name, permission=permission_for_route(method, path).value)
                if not protected:
                    errors.append(f"protected route has no authentication dependency: {method} {path}")
            rows.append(row)
    # Rules may deliberately classify a route family before every method exists;
    # that is not a stale policy. Public liveness endpoints outside /api/v1 are
    # likewise outside this checker's scoped registry.
    return {
        "schema_version": "1.0",
        "status": "pass" if not errors else "fail",
        "route_count": len(rows),
        "routes": sorted(rows, key=lambda row: (row["path"], row["method"])),
        "errors": sorted(set(errors)),
    }


# Compatibility name used by the focused security suite.
inspect_routes = build_report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = build_report()
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
