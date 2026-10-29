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
