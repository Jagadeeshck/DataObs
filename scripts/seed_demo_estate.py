#!/usr/bin/env python3
"""Seed a coherent, end-to-end demo estate into the canonical Console read-models.

This is NOT a fake-UI shim: it writes realistic, tenant/environment-scoped documents
into the same durable v1 read-model indices that a live DataObs collection runtime
writes — assets, quality, freshness, lineage, stream clusters, and incidents. The
Command Center projector then aggregates them into the six-pillar estate view exactly
as it would for real collected telemetry, and every pillar page in the Console renders
from this data.

The estate tells one consistent story for the `acme-retail / production` tenant:
a retail data platform where an upstream freshness breach on `orders` cascades into a
failing quality check and an open P1 incident, with lineage and a Kafka cluster showing
the pipeline context. A second tenant (`northstar / staging`) is healthy, to demonstrate
tenant isolation and a green estate side by side.

Run:
  python scripts/seed_demo_estate.py
Idempotent: deterministic doc ids mean re-running overwrites rather than duplicates.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from packages.elastic_store.client import make_client


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _write(es, index: str, doc_id: str, document: dict) -> None:
    es.index(index=index, id=doc_id, document=document)


def seed_tenant(es, tenant: str, environment: str, *, degraded: bool) -> None:
    """Seed one tenant's estate. degraded=True injects a realistic incident cascade."""
    now = datetime.now(timezone.utc)
    base = {"tenant_id": tenant, "environment": environment, "@timestamp": _iso(now)}

    # ── Assets (Data pillar catalog) ───────────────────────────────────────
    assets = [
        ("orders", "table", "warehouse.public.orders", "data-engineering"),
        ("order_items", "table", "warehouse.public.order_items", "data-engineering"),
        ("customers", "table", "warehouse.public.customers", "data-engineering"),
        ("daily_revenue", "view", "warehouse.analytics.daily_revenue", "analytics"),
        ("orders_stream", "stream", "kafka.orders.v1", "platform"),
    ]
    for aid, atype, fqn, owner in assets:
        _write(
            es,
            "dataobs-assets-v1-write",
            f"{tenant}:{aid}",
            {
                **base,
                "asset_id": aid,
                "id": aid,
                "name": fqn,
                "display_name": fqn,
                "asset_type": atype,
                "owner_team": owner,
                "classification": "internal",
                "business_service": "retail-orders",
                "description": f"{aid} {fqn} {atype} retail orders",
                "tags": {"domain": "retail", "asset_type": atype},
                "observed_at": _iso(now),
            },
        )

    # ── Quality checks (Data pillar) ───────────────────────────────────────
    # orders: a failing null-rate check when degraded; everything else passes.
    quality_rows = [
        ("orders", "null_rate", "fail" if degraded else "pass", 0.18 if degraded else 0.002),
        ("orders", "row_count", "pass", 1_240_391),
        ("order_items", "row_count", "pass", 5_902_114),
        ("customers", "uniqueness", "pass", 1.0),
        ("daily_revenue", "freshness", "pass", 1.0),
    ]
    for aid, check_type, status, value in quality_rows:
        _write(
            es,
            "dataobs-quality-current-v1-write",
            f"{tenant}:{aid}:{check_type}",
            {
                **base,
                "asset_id": aid,
                "monitor_type": check_type,
                "status": status,
                "severity": "high" if status == "fail" else "low",
                "value": value,
                "observed_at": _iso(now),
            },
        )

    # ── Freshness (Data pillar) ────────────────────────────────────────────
    freshness_rows = [
        ("orders", "stale" if degraded else "fresh", 9100 if degraded else 120),
        ("order_items", "fresh", 180),
        ("customers", "fresh", 3600),
        ("daily_revenue", "fresh", 900),
    ]
    for aid, status, age in freshness_rows:
        _write(
            es,
            "dataobs-freshness-current-v1-write",
            f"{tenant}:{aid}",
            {
                **base,
                "asset_id": aid,
                "status": status,
                "lag_seconds": age,
                "threshold": 3600,
                "observed_at": _iso(now),
            },
        )

    # ── Lineage (Data Pipeline pillar) ─────────────────────────────────────
    lineage_edges = [
        ("orders_stream", "orders"),
        ("orders", "order_items"),
        ("orders", "daily_revenue"),
        ("customers", "daily_revenue"),
    ]
    for i, (src, dst) in enumerate(lineage_edges):
        _write(
            es,
            "dataobs-lineage-current-v1-write",
            f"{tenant}:edge-{i}",
            {
                **base,
                "id": f"edge-{i}",
                "source_node_id": src,
                "destination_node_id": dst,
                "confidence": 1.0,
                "observed_at": _iso(now),
            },
        )

    # ── Pathway topology (Flow map / Data Pipeline) ────────────────────────
    nodes = [
        ("orders_stream", "stream"),
        ("orders", "dataset"),
        ("order_items", "dataset"),
        ("customers", "dataset"),
        ("daily_revenue", "dataset"),
    ]
    for nid, kind in nodes:
        node_health = "critical" if (degraded and nid == "orders") else "healthy"
        _write(
            es,
            "dataobs-pathway-nodes-v1-write",
            f"{tenant}:{nid}",
            {**base, "id": nid, "name": nid, "asset_type": kind, "status": node_health, "health_state": node_health},
        )
    for i, (src, dst) in enumerate(lineage_edges):
        _write(
            es,
            "dataobs-pathway-definitions-v1-write",
            f"{tenant}:pdef-{i}",
            {**base, "id": f"pdef-{i}", "source_node_id": src, "destination_node_id": dst},
        )

    # ── Stream cluster (Platform pillar) ───────────────────────────────────
    _write(
        es,
        "dataobs-stream-clusters-v1-write",
        f"{tenant}:kafka-prod",
        {
            **base,
            "cluster_id": "kafka-prod",
            "name": "retail-kafka-prod",
            "status": "degraded" if degraded else "healthy",
            "health_state": "degraded" if degraded else "healthy",
            "observed_at": _iso(now),
        },
    )

    # ── Incident (priority queue) — only in the degraded tenant ────────────
    if degraded:
        opened = now - timedelta(minutes=37)
        _write(
            es,
            "dataobs-incidents-v1-write",
            f"{tenant}:inc-orders-freshness",
            {
                **base,
                "incident_id": "inc-orders-freshness",
                "id": "inc-orders-freshness",
                "title": "orders freshness SLA breach cascading to null-rate failure",
                "summary": "orders is 2h32m stale; downstream null_rate check failing",
                "state": "open",
                "severity": "critical",
                "primary_resource": "orders",
                "affected_assets": ["orders", "daily_revenue"],
                "pillar": "data",
                "owner": "data-engineering",
                "opened_at": _iso(opened),
                "created_at": _iso(opened),
                "impact_summary": "daily_revenue view may be understated",
                "notification_state": "notified: slack #data-oncall",
            },
        )


def main() -> None:
    es = make_client()
    tenants = [
        ("acme-retail", "production", True),
        ("northstar", "staging", False),
    ]
    for tenant, environment, degraded in tenants:
        seed_tenant(es, tenant, environment, degraded=degraded)
    es.indices.refresh(index="dataobs-*")

    # Project the Command Center summary immediately so the estate view is populated
    # without waiting for the first worker cycle.
    try:
        from services.command_center.projector import CommandCenterProjector

        projector = CommandCenterProjector(es)
        for tenant, environment, _ in tenants:
            projector.project(tenant, environment)
    except Exception as exc:  # projector optional at seed time
        print(f"note: command-center projection deferred to worker ({exc})")

    print("Seeded coherent demo estate for 2 tenants across all collected pillars.")
    print("  acme-retail/production: degraded (freshness → quality → P1 incident cascade)")
    print("  northstar/staging:      healthy")


if __name__ == "__main__":
    main()
