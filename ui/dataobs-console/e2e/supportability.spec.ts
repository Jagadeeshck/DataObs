import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page, type Request } from "@playwright/test";

const responses: Record<string, unknown> = {
  support: {
    support_profile: "unvalidated",
    evidence_freshness: "stale",
    release_decision: "NO_GO",
    known_blockers: [],
    kubernetes_support_state: "supported",
    elasticsearch_support_state: "unvalidated",
    oidc_support_state: "unknown",
    ha_profile: "supported",
    capacity_profile: "unvalidated",
  },
  diagnostics: {
    state: "degraded",
    checks: [
      {
        id: "backup_freshness",
        state: "unknown",
        severity: "SEV2",
        reason_code: "BACKUP_EVIDENCE_UNAVAILABLE",
        remediation_code: "VERIFY_BACKUP_EVIDENCE",
      },
    ],
  },
  configuration: {
    schema_version: "1.0",
    fingerprint: "sha256:safe-evidence",
    drift_state: "unknown",
    changed_categories: [],
    password: "must-not-render",
  },
  maintenance: {
    state: "normal",
    reason_code: "NO_MAINTENANCE_DECLARED",
    start: null,
    expected_end: null,
  },
  "known-issues": {
    count: 1,
    items: [
      {
        issue_id: "KNOWN-1",
        title: "Bounded issue",
        affected_versions: "1.x",
        affected_component: "api",
        severity: "SEV2",
        state: "open",
        workaround_reference: null,
        fixed_version: null,
        owner_team: "Team 0",
        token: "must-not-render",
      },
    ],
  },
  "operational-readiness": {
    state: "NO_GO",
    categories: [
      {
        category: "backup_restore",
        state: "unknown",
        evidence: "evidence unavailable",
      },
      {
        category: "runtime_security",
        state: "failed",
        evidence: "validation failed",
      },
    ],
  },
};

async function mockOperator(page: Page, requests: Request[]) {
  page.on("request", (request) => requests.push(request));
  await page.route("**/api/v1/auth/me", (route) =>
    route.fulfill({
      json: {
        subject: "operator",
        display_name: "Platform Operator",
        permissions: ["platform_operations:read"],
        tenants: [],
      },
    }),
  );
  await page.route("**/api/v1/platform/*", (route) => {
    const section = new URL(route.request().url()).pathname.split("/").at(-1)!;
    return route.fulfill({ json: responses[section] });
  });
}

test("NO_GO, stale, unknown and safe evidence remain truthful and read-only", async ({
  page,
}) => {
  const requests: Request[] = [];
  await mockOperator(page, requests);
  await page.goto("/administration/platform/readiness");
  await expect(
    page.getByRole("heading", { name: "Operational Readiness", exact: true }),
  ).toBeVisible();
  await expect(page.getByText("NO GO", { exact: true })).toBeVisible();
  await expect(page.getByText("Current evidence: Stale")).toBeVisible();
  await expect(page.getByText(/UNKNOWN — evidence unavailable/)).toBeVisible();
  expect(requests.filter((request) => request.method() !== "GET")).toEqual([]);
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  await page.screenshot({
    path: "artifacts/team-5-operational-readiness.png",
    fullPage: true,
  });
});

test("supportability uses typed fields and never renders accidental secrets", async ({
  page,
}) => {
  const requests: Request[] = [];
  await mockOperator(page, requests);
  await page.goto("/administration/platform/supportability");
  await expect(
    page.getByRole("heading", { name: "Platform Supportability" }),
  ).toBeVisible();
  await expect(page.getByText("Support Profile")).toBeVisible();
  await expect(page.getByText("must-not-render")).toHaveCount(0);
  await expect(
    page.getByText(/not exposed through the Console API/),
  ).toBeVisible();
  expect(requests.filter((request) => request.method() !== "GET")).toEqual([]);
});

test("ordinary tenant user cannot see or open supportability", async ({
  page,
}) => {
  await page.route("**/api/v1/auth/me", (route) =>
    route.fulfill({
      json: { subject: "tenant", permissions: ["console:read"], tenants: [] },
    }),
  );
  let platformCalls = 0;
  await page.route("**/api/v1/platform/*", (route) => {
    platformCalls += 1;
    return route.abort();
  });
  await page.goto("/administration/platform/supportability");
  await expect(page.getByText(/permission|access/i)).toBeVisible();
  expect(platformCalls).toBe(0);
});
