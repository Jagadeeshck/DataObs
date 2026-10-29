import type { Page } from "@playwright/test";

export const releaseTenant = {
  id: "verified-tenant",
  name: "Verified tenant",
  environments: ["prod", "stage"],
};

const defaultPermissions = [
  "console:read",
  "integrations:read",
  "incidents:read",
  "iam:read",
  "auth:read",
  "platform_operations:read",
];

export async function mockReleaseAuth(
  page: Page,
  permissions: string[] = defaultPermissions,
) {
  await page.route("**/api/v1/**", (route) =>
    route.fulfill({
      status: 404,
      contentType: "application/json",
      body: JSON.stringify({
        detail: { code: "not_configured", message: "No release fixture for this endpoint" },
      }),
    }),
  );
  await page.route("**/api/v1/auth/config", (route) =>
    route.fulfill({ json: { provider: "disabled", scopes: [] } }),
  );
  await page.route("**/api/v1/auth/me", (route) =>
    route.fulfill({
      json: {
        subject: "release-tester",
        display_name: "Release Tester",
        permissions,
        tenants: [releaseTenant],
      },
    }),
  );
}

export async function mockReleaseShell(page: Page) {
  await mockReleaseAuth(page);
  await page.route("**/api/v1/command-center?**", (route) =>
    route.fulfill({
      json: {
        overall_health: "unknown",
        pillars: [],
        priority_items: [],
        recent_changes: [],
        data_status: {
          complete: false,
          warnings: ["Release fixture has no live evidence"],
          sources: [],
          observed_at: null,
          missing_inputs: ["hosted-runtime"],
        },
      },
    }),
  );
  await page.route("**/api/v1/topology?**", (route) =>
    route.fulfill({
      json: {
        nodes: [],
        edges: [],
        truncated: false,
        data_status: {
          complete: false,
          warnings: ["Release fixture has no live topology"],
          sources: [],
          observed_at: null,
          missing_inputs: ["hosted-runtime"],
        },
      },
    }),
  );
  await page.route("**/api/v1/integrations/metadata?**", (route) =>
    route.fulfill({ json: { items: [] } }),
  );
}

export async function mockDataProductRelease(page: Page) {
  await mockReleaseAuth(page);
  const product = {
    id: "seed-product",
    name: "Seed product",
    description: "Release acceptance fixture",
    domain: "orders",
    criticality: "high",
    lifecycle_state: "active",
    owner: { team: "Team 2" },
    outputs: [],
    revision: 1,
    etag: "fixture-etag",
    updated_at: "2026-10-28T00:00:00Z",
  };
  await page.route("**/api/v1/data-products?**", (route) =>
    route.fulfill({
      json: {
        items: [product],
        data_status: "complete",
        warnings: [],
        pagination: { limit: 50, next_cursor: null },
      },
    }),
  );
  await page.route(/\/api\/v1\/data-products\/(seed-product|demo)\?/, (route) =>
    route.fulfill({
      json: {
        product: { ...product, id: route.request().url().includes("/demo?") ? "demo" : "seed-product" },
        data_status: "complete",
        warnings: [],
      },
    }),
  );
  await page.route(/\/api\/v1\/data-products\/(seed-product|demo)\/(members|dependencies|revisions)(\?|$)/, (route) =>
    route.fulfill({ json: { items: [], truncated: false, next_cursor: null } }),
  );
  await page.route(/\/api\/v1\/data-products\/(seed-product|demo)\/dependencies\/upstream\?/, (route) =>
    route.fulfill({ json: { edges: [], truncated: false, next_cursor: null } }),
  );
}


export async function mockCriticalJourneys(page: Page) {
  await mockReleaseShell(page);

  const observedAt = "2026-10-28T12:00:00Z";
  const monitor = {
    id: "monitor-1",
    name: "Orders freshness",
    tenant_id: releaseTenant.id,
    environment: "prod",
    monitor_type: "freshness",
    target: {
      asset_id: "asset-orders",
      source_type: "deterministic_test",
      columns: [],
      parameters: {},
    },
    schedule: { interval: "5m", timezone: "UTC" },
    threshold: { mode: "fixed", maximum: 900 },
    alert: { severity: "high", consecutive_breaches: 1 },
    managed_by: "console-user",
    revision: 1,
    etag: "monitor-etag-1",
    state: "active",
  };

  await page.route("**/api/v1/assets?**", (route) =>
    route.fulfill({
      json: {
        items: [
          {
            id: "asset-orders",
            name: "orders",
            fqn: "warehouse.public.orders",
            asset_type: "table",
            health: "degraded",
            owner_team: "payments",
            business_service: "checkout",
            source: "postgresql",
            environment: "prod",
            last_observed: observedAt,
          },
        ],
        next_cursor: null,
        data_status: "complete",
        warnings: [],
      },
    }),
  );
  await page.route("**/api/v1/assets/asset-orders/summary?**", (route) =>
    route.fulfill({
      json: {
        data_status: "complete",
        confidence: 0.98,
        name: "orders",
        fqn: "warehouse.public.orders",
        asset_type: "table",
        health: "degraded",
        owner_team: "payments",
        business_service: "checkout",
        source: "postgresql",
        environment: "prod",
        freshness: "breaching",
        quality: "degraded",
        active_incidents: 1,
        upstream_count: 1,
        downstream_count: 2,
      },
    }),
  );

  await page.route("**/api/v1/quality/capabilities?**", (route) =>
    route.fulfill({
      json: {
        items: [
          {
            monitor_type: "freshness",
            display_name: "Freshness",
            executable: true,
            capability_state: "available",
            target_requirements: [],
            supported_data_sources: ["deterministic_test"],
            required_parameters: [],
            threshold_modes: ["fixed"],
            baseline_support: false,
          },
        ],
      },
    }),
  );
  await page.route("**/api/v1/quality/monitors?**", (route) =>
    route.fulfill({ json: { items: [monitor], next_cursor: null } }),
  );
  await page.route("**/api/v1/quality/monitors/monitor-1?**", (route) =>
    route.fulfill({
      headers: { ETag: '"monitor-etag-1"' },
      json: monitor,
    }),
  );

  await page.route("**/api/v1/jobs?**", (route) =>
    route.fulfill({
      json: {
        items: [
          {
            job_id: "job-orders",
            qualified_name: "orders.daily",
            platform: "airflow",
            owner: "payments",
            state: "failed",
            last_seen: observedAt,
            duration_ms: 125000,
          },
        ],
        next_cursor: null,
      },
    }),
  );
  await page.route("**/api/v1/jobs/job-orders?**", (route) =>
    route.fulfill({
      json: {
        job_id: "job-orders",
        qualified_name: "orders.daily",
        platform: "airflow",
        owner: "payments",
        state: "failed",
        last_seen: observedAt,
        missing_run: { state: "unknown", reason: "insufficient schedule evidence" },
      },
    }),
  );
  await page.route("**/api/v1/runs/run-orders?**", (route) =>
    route.fulfill({
      json: {
        run_id: "run-orders",
        job_id: "job-orders",
        state: "failed",
        started_at: "2026-10-28T11:55:00Z",
        ended_at: observedAt,
        duration_ms: 300000,
      },
    }),
  );

  await page.route("**/api/v1/streams/providers?**", (route) =>
    route.fulfill({
      json: {
        items: [
          {
            provider: "kafka",
            messaging_system: "kafka",
            configured: true,
            contract_capability: "available",
            collection_capability: "complete",
            runtime_state: "available",
            data_freshness: "fresh",
            capabilities: {
              inventory: "supported",
              throughput: "supported",
              backlog: "supported",
              lag: "supported",
              retention: "supported",
            },
            limitations: [],
            latest_observation: observedAt,
            source_coverage: 1,
          },
        ],
        data_status: "complete",
        warnings: [],
      },
    }),
  );
  await page.route("**/api/v1/streams?**", (route) =>
    route.fulfill({
      json: {
        items: [
          {
            stream_id: "orders-topic",
            topic: "orders.events",
            name: "orders.events",
            cluster_id: "kafka-prod",
            health: "degraded",
            maximum_lag: 120,
            retention_risk: "at_risk",
            partition_count: 12,
            replication_factor: 3,
            producer_rate: 1000,
            consumer_rate: 800,
            records_per_second: 1000,
            observed_at: observedAt,
          },
        ],
        next_cursor: null,
        data_status: "complete",
        warnings: [],
        source_coverage: ["kafka"],
      },
    }),
  );

  const evidence = {
    data_status: "complete",
    observed_at: observedAt,
    source_coverage: ["openlineage"],
    confidence: 0.9,
    warnings: [],
    missing_inputs: [],
  };
  await page.route("**/api/v1/pathways?**", (route) =>
    route.fulfill({
      json: {
        items: [
          {
            pathway_id: "path-orders",
            name: "Orders ingestion",
            classification: "complete",
            health: "degraded",
            node_ids: ["source", "asset-orders"],
            edge_ids: ["edge-1"],
            node_count: 2,
            edge_count: 1,
            truncated: false,
            owner_team: "payments",
            business_service: "checkout",
            last_seen: observedAt,
            ...evidence,
          },
        ],
        next_cursor: null,
        ...evidence,
      },
    }),
  );
  await page.route("**/api/v1/pathways/path-orders?**", (route) =>
    route.fulfill({
      json: {
        pathway_id: "path-orders",
        name: "Orders ingestion",
        classification: "complete",
        health: "degraded",
        node_ids: ["source", "asset-orders"],
        edge_ids: ["edge-1"],
        truncated: false,
        ...evidence,
      },
    }),
  );
  await page.route("**/api/v1/pathways/path-orders/topology?**", (route) =>
    route.fulfill({
      json: {
        pathway_id: "path-orders",
        node_ids: ["source", "asset-orders"],
        edge_ids: ["edge-1"],
        nodes: [
          { node_id: "source", name: "orders-source", node_type: "dataset", health: "healthy", confidence: 0.9 },
          { node_id: "asset-orders", name: "orders", node_type: "dataset", health: "degraded", confidence: 0.9 },
        ],
        edges: [
          {
            edge_id: "edge-1",
            source_node_id: "source",
            destination_node_id: "asset-orders",
            edge_type: "lineage",
            health: "degraded",
            confidence: 0.9,
            metrics: { latency_ms: 250 },
            evidence_refs: ["fixture:evidence"],
          },
        ],
        ...evidence,
      },
    }),
  );
  await page.route("**/api/v1/pathways/path-orders/latency?**", (route) =>
    route.fulfill({
      json: {
        pathway_id: "path-orders",
        method: "edge_estimate",
        p50_ms: 100,
        p95_ms: 250,
        p99_ms: 300,
        sample_count: 10,
        missing_segments: [],
        ...evidence,
      },
    }),
  );
  await page.route("**/api/v1/pathways/path-orders/bottlenecks?**", (route) =>
    route.fulfill({
      json: {
        items: [
          {
            edge_id: "edge-1",
            view: "latency",
            contribution_percentage: 80,
            absolute_contribution: 200,
            confidence: 0.9,
            calculation_method: "bounded_fixture",
            health_explanation: "Observed degraded edge",
          },
        ],
        root_cause_claimed: false,
        ...evidence,
      },
    }),
  );
  await page.route("**/api/v1/pathways/path-orders/impact?**", (route) =>
    route.fulfill({
      json: {
        items: [
          {
            resource_id: "incident-orders",
            resource_type: "incident",
            name: "Orders freshness breach",
            classification: "direct",
            active: true,
          },
        ],
        active_incidents: [
          {
            resource_id: "incident-orders",
            resource_type: "incident",
            name: "Orders freshness breach",
            classification: "direct",
            active: true,
          },
        ],
        ...evidence,
      },
    }),
  );
  await page.route("**/api/v1/pathway-slos?**", (route) =>
    route.fulfill({ json: { items: [], next_cursor: null, ...evidence } }),
  );

  const incident = {
    id: "incident-orders",
    title: "Orders freshness breach",
    state: "investigating",
    severity: "high",
    owner: "payments-oncall",
    business_service: "checkout",
    affected_assets: ["asset-orders"],
    affected_asset_count: 1,
    occurrence_count: 2,
    opened_at: "2026-10-28T11:50:00Z",
    last_observed_at: observedAt,
    data_status: "complete",
    severity_factors: { quality: "breached" },
    impact_summary: "Orders data is stale.",
    first_observed_at: "2026-10-28T11:50:00Z",
    finding_references: ["finding-orders"],
    latest_evidence: [{ kind: "freshness", state: "breached" }],
    correlation_key: "orders-freshness",
    revision: "1",
    evidence_coverage: "complete",
    warnings: [],
    missing_inputs: [],
    request_id: "fixture-request",
  };
  await page.route("**/api/v1/incident-workbench?**", (route) =>
    route.fulfill({
      json: {
        items: [incident],
        next_cursor: null,
        data_status: "complete",
        warnings: [],
      },
    }),
  );
  await page.route("**/api/v1/incident-workbench/incident-orders?**", (route) =>
    route.fulfill({ json: incident }),
  );
  await page.route("**/api/v1/incident-workbench/incident-orders/timeline?**", (route) =>
    route.fulfill({
      json: {
        items: [
          {
            event_id: "event-1",
            event_type: "finding",
            timestamp: observedAt,
            actor: "dataobs",
            summary: "Freshness finding linked",
          },
        ],
      },
    }),
  );

  await page.route("**/api/v1/integrations/metadata?**", (route) =>
    route.fulfill({
      json: {
        items: [
          {
            id: "postgresql",
            name: "PostgreSQL",
            category: "database",
            support_status: "preview",
            configuration_state: "configured",
            connection_state: "connected",
            last_successful_collection: observedAt,
            coverage: 85,
            required_permissions: ["read metadata"],
            purpose: "Collect bounded metadata and quality evidence.",
            data_collected: ["metadata"],
            data_not_collected: ["raw row payloads"],
            network_access: ["backend only"],
            secret_handling: "Backend-managed secret reference",
          },
        ],
      },
    }),
  );
}
