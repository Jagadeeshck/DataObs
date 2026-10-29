import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import { mockCriticalJourneys, mockReleaseShell } from "./fixtures/release";

const seriousOrCritical = async (page: Parameters<typeof AxeBuilder>[0]["page"]) =>
  (await new AxeBuilder({ page }).analyze()).violations.filter((violation) =>
    ["serious", "critical"].includes(violation.impact ?? ""),
  );

test.describe("v0.2.0 critical Console journeys", () => {
  test.beforeEach(async ({ page }) => mockCriticalJourneys(page));

  test("asset inventory opens Asset 360 without losing evidence truth", async ({
    page,
  }) => {
    await page.goto("/assets");
    await expect(
      page.getByRole("heading", { name: "Asset Catalog" }),
    ).toBeVisible();
    await page.getByRole("link", { name: "warehouse.public.orders" }).click();
    await expect(page.getByRole("heading", { name: "asset-orders" })).toBeVisible();
    await expect(page.getByText("degraded", { exact: true }).first()).toBeVisible();
    expect(await seriousOrCritical(page)).toEqual([]);
  });

  test("Quality inventory, authoring and monitor investigation remain usable", async ({
    page,
  }) => {
    await page.goto("/quality/monitors");
    await expect(
      page.getByRole("heading", { name: "Monitor inventory" }),
    ).toBeVisible();
    await page.getByRole("link", { name: "Orders freshness" }).click();
    await expect(
      page.getByRole("heading", { name: "Orders freshness" }),
    ).toBeVisible();

    await page.goto("/quality/monitors/new");
    await expect(
      page.getByRole("heading", { name: "Create draft monitor" }),
    ).toBeVisible();
    await expect(page.getByRole("option", { name: "Freshness" })).toBeAttached();
    expect(await seriousOrCritical(page)).toEqual([]);
  });

  test("Jobs, Run 360 and lineage context are reachable from the trusted scope", async ({
    page,
  }) => {
    await page.goto("/jobs");
    await expect(page.getByRole("heading", { name: "Jobs" })).toBeVisible();
    await page.getByRole("link", { name: "orders.daily" }).click();
    await expect(page.getByRole("heading", { name: "Job 360" })).toBeVisible();
    await expect(page.getByText("failed", { exact: true })).toBeVisible();

    await page.goto("/runs/run-orders");
    await expect(page.getByRole("heading", { name: "Run 360" })).toBeVisible();

    await page.goto("/lineage");
    await expect(
      page.getByRole("heading", { name: "Lineage Explorer" }),
    ).toBeVisible();
    await expect(
      page.getByRole("heading", { name: "Accessible graph alternative" }),
    ).toBeVisible();
    expect(await seriousOrCritical(page)).toEqual([]);
  });

  test("Messaging and Pathway investigation preserve degraded evidence", async ({
    page,
  }) => {
    await page.goto("/streams");
    await expect(
      page.getByRole("heading", { name: "Streams Inventory" }),
    ).toBeVisible();
    await expect(page.getByRole("link", { name: "orders.events" })).toBeVisible();
    await expect(page.getByText("At risk", { exact: true }).first()).toBeVisible();

    await page.goto("/pathways");
    await expect(
      page.getByRole("heading", { name: "Pathway inventory" }),
    ).toBeVisible();
    await page.getByRole("link", { name: "Orders ingestion" }).click();
    await expect(
      page.getByRole("heading", { name: "Orders ingestion" }),
    ).toBeVisible();
    await expect(page.getByText("degraded", { exact: true }).first()).toBeVisible();
    expect(await seriousOrCritical(page)).toEqual([]);
  });

  test("Incident Inbox opens the related Incident Workbench", async ({ page }) => {
    await page.goto("/incidents");
    await expect(
      page.getByRole("heading", { name: "Incident Inbox" }),
    ).toBeVisible();
    await page.getByRole("link", { name: "Orders freshness breach" }).click();
    await expect(
      page.getByRole("heading", { name: "Orders freshness breach" }),
    ).toBeVisible();
    await expect(page.getByRole("heading", { name: "Timeline" })).toBeVisible();
    await expect(
      page.getByText("Freshness finding linked", { exact: false }),
    ).toBeVisible();
    expect(await seriousOrCritical(page)).toEqual([]);
  });

  test("Integration metadata and first-run onboarding remain truthful", async ({
    page,
  }) => {
    await page.goto("/integrations");
    await expect(
      page.getByRole("heading", { name: "Integrations", exact: true }),
    ).toBeVisible();
    await page.getByRole("link", { name: "Manage integration" }).click();
    await expect(page.getByRole("heading", { name: "PostgreSQL" })).toBeVisible();
    await expect(page.getByText("preview", { exact: false }).first()).toBeVisible();

    await page.goto("/onboarding");
    await expect(page.getByRole("heading").first()).toBeVisible();
    expect(await seriousOrCritical(page)).toEqual([]);
  });
});

test.describe("v0.2.0 security and trusted-context acceptance", () => {
  test("URL tenant/environment values cannot override trusted request scope", async ({
    page,
  }) => {
    await mockReleaseShell(page);
    const seen: Array<{ tenant: string | null; environment: string | null }> = [];
    await page.route("**/api/v1/command-center?**", (route) => {
      const url = new URL(route.request().url());
      seen.push({
        tenant: route.request().headers()["x-dataobs-tenant"] ?? null,
        environment: url.searchParams.get("environment"),
      });
      return route.fulfill({
        json: {
          overall_health: "unknown",
          pillars: [],
          priority_items: [],
          recent_changes: [],
          data_status: {
            complete: false,
            warnings: ["Scoped fixture"],
            sources: [],
            observed_at: null,
            missing_inputs: [],
          },
        },
      });
    });

    await page.goto("/?tenant=other-tenant&environment=other-env");
    await expect(
      page.getByText("Verified tenant / prod", { exact: true }),
    ).toBeVisible();
    await expect.poll(() => seen.length).toBeGreaterThan(0);
    expect(seen.at(-1)).toEqual({
      tenant: "verified-tenant",
      environment: "prod",
    });

    await page.getByText("Verified tenant / prod", { exact: true }).click();
    await page
      .getByLabel("Environment", { exact: true })
      .selectOption("stage");
    await expect
      .poll(() => seen.at(-1)?.environment)
      .toBe("stage");
    expect(seen.at(-1)?.tenant).toBe("verified-tenant");
  });

  test("expired or unauthorised auth context fails closed before capability data loads", async ({
    page,
  }) => {
    await mockReleaseShell(page);
    let capabilityCalls = 0;
    await page.route("**/api/v1/command-center?**", (route) => {
      capabilityCalls += 1;
      return route.fulfill({ status: 500, json: { detail: "must not load" } });
    });
    await page.route("**/api/v1/auth/me", (route) =>
      route.fulfill({ status: 401, json: { detail: "expired" } }),
    );

    await page.goto("/");
    await expect(
      page.getByRole("heading", { name: "Access denied" }),
    ).toBeVisible();
    expect(capabilityCalls).toBe(0);
  });
});
