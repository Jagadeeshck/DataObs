#!/usr/bin/env python3
"""
Per-tenant Grafana Alloy config overlay generator.

Usage::

    python tools/alloy-config-gen/generate.py \
        --tenants tools/alloy-config-gen/tenants/ \
        --base tools/alloy-config-gen/base_config.alloy \
        --output output/

Resolves: https://github.com/Jagadeeshck/DataObs/issues/31
"""
from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

import yaml


def load_tenant(path: Path) -> dict:
    with path.open() as f:
        return yaml.safe_load(f)


def render_tenant_config(base: str, tenant: dict) -> str:
    """
    Append per-tenant routing and remote-write blocks to base config.

    Credentials are referenced as env vars — never inlined.
    """
    tenant_id = tenant["tenant_id"]
    remote_url = tenant.get("prometheus_remote_write_url", "")
    otlp_port = tenant.get("otlp_port", 4317)
    labels = tenant.get("labels", {})

    label_str = ", ".join(f'"{k}" = "{v}"' for k, v in labels.items())

    routing_block = f"""
// ── Tenant: {tenant_id} ──────────────────────────────────────────────────────

otelcol.receiver.otlp "{tenant_id}" {{
  grpc {{
    endpoint = "0.0.0.0:{otlp_port}"
  }}
  output {{
    metrics = [otelcol.processor.batch.{tenant_id}.input]
    traces  = [otelcol.processor.batch.{tenant_id}.input]
    logs    = [otelcol.processor.batch.{tenant_id}.input]
  }}
}}

otelcol.processor.batch "{tenant_id}" {{
  output {{
    metrics = [otelcol.exporter.prometheus.{tenant_id}.input]
    traces  = [otelcol.exporter.otlp.{tenant_id}.input]
    logs    = [otelcol.exporter.otlp.{tenant_id}.input]
  }}
}}

prometheus.remote_write "{tenant_id}" {{
  endpoint {{
    url = "{remote_url}"
    headers = {{
      "X-Tenant-ID" = "{tenant_id}",
    }}
    basic_auth {{
      username = env("DATAOBS_{tenant_id.upper()}_PROM_USER")
      password = env("DATAOBS_{tenant_id.upper()}_PROM_PASS")
    }}
  }}
  external_labels = {{ {label_str} }}
}}
"""
    return base + routing_block


def validate_alloy_config(path: Path) -> bool:
    result = subprocess.run(
        ["alloy", "fmt", "--test", str(path)],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate per-tenant Alloy configs")
    parser.add_argument("--tenants", default="tools/alloy-config-gen/tenants/")
    parser.add_argument("--base", default="tools/alloy-config-gen/base_config.alloy")
    parser.add_argument("--output", default="output/alloy-configs/")
    args = parser.parse_args()

    base = Path(args.base).read_text()
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    tenant_dir = Path(args.tenants)
    tenants = list(tenant_dir.glob("*.yaml"))
    if not tenants:
        print(f"No tenant YAML files found in {tenant_dir}")
        return

    for tenant_file in tenants:
        tenant = load_tenant(tenant_file)
        tenant_id = tenant["tenant_id"]
        config = render_tenant_config(base, tenant)

        out_path = output_dir / f"{tenant_id}.alloy"
        out_path.write_text(config)
        print(f"Generated: {out_path}")

        valid = validate_alloy_config(out_path)
        print(f"  alloy fmt --test: {'OK' if valid else 'FAILED'}")


if __name__ == "__main__":
    main()
