#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from fastapi.routing import APIRoute

from src.api.app import create_app
from src.security.route_policy import PUBLIC_ROUTES, ROUTE_PERMISSIONS

ignored = {"/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc"}
missing = []
for route in create_app().routes:
    if not isinstance(route, APIRoute) or route.path in ignored:
        continue
    for method in route.methods:
        key = (method, route.path)
        if key not in PUBLIC_ROUTES and key not in ROUTE_PERMISSIONS:
            missing.append(key)
if missing:
    raise SystemExit("routes missing explicit security policy: " + repr(sorted(missing)))
print(f"route policy valid: {len(ROUTE_PERMISSIONS)} protected, {len(PUBLIC_ROUTES)} public")
