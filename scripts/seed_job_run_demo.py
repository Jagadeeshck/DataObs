#!/usr/bin/env python3
"""Emit deterministic, synthetic metadata only; never business rows."""

import json

print(
    json.dumps(
        {
            "tenants": ["demo-a", "demo-b"],
            "environments": ["dev", "prod"],
            "overlapping_job": "daily_orders",
            "status": "fixture_ready",
        }
    )
)
