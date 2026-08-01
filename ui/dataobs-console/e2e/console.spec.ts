import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";
const status = {
  complete: false,
  warnings: ["Cost evidence is not configured"],
  sources: ["pathways"],
  observed_at: "2026-08-01T00:00:00Z",
  missing_inputs: ["finops"],
};
async function mockConsole(page: Page) {
  await page.route("**/api/v1/auth/me", (route) =>
    route.fulfill({
      json: {
        subject: "test-user",
        display_name: "Console Tester",
        permissions: ["integrations:read"],
        tenants: [
          {
            id: "verified-tenant",
            name: "Verified tenant",
            environments: ["prod", "stage"],
          },
        ],
      },
    }),
  );
  await page.route("**/api/v1/command-center?**", (route) =>
    route.fulfill({
      json: {
        overall_health: "unknown",
        pillars: [
          "platform",
          "data_pipeline",
          "data",
          "finops_cost",
          "business",
          "ai_agent",
        ].map((id) => ({ id, name: id, health: "unknown", metric: "Unknown" })),
        priority_items: [],
        recent_changes: [],
        data_status: status,
      },
    }),
  );
  await page.route("**/api/v1/topology?**", (route) =>
    route.fulfill({
      json: {
        nodes: [
          { id: "dataset", name: "orders", type: "dataset", health: "unknown" },
        ],
        edges: [],
        truncated: true,
        data_status: status,
      },
    }),
  );
  await page.route("**/api/v1/integrations/metadata?**", (route) =>
    route.fulfill({ json: { items: [] } }),
  );
}
test.beforeEach(async ({ page }) => mockConsole(page));
test("authenticated shell, context, command center and route recovery are accessible", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Command Center" }),
  ).toBeVisible();
  await expect(page.getByLabel("Tenant")).toHaveValue("verified-tenant");
  await page.getByLabel("Environment").selectOption("stage");
  await expect(page).toHaveURL(/environment=stage/);
  await page.keyboard.press("Tab");
  await expect(page.locator(":focus")).toBeVisible();
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  await page.goto("/missing");
  await expect(
    page.getByRole("heading", { name: "Page not found" }),
  ).toBeVisible();
});
test("data flow exposes bounded graph as an equivalent table", async ({
  page,
}) => {
  await page.goto("/flow");
  await expect(page.getByText(/Topology was truncated/)).toBeVisible();
  await page.getByRole("button", { name: /Accessible list/ }).click();
  await expect(page.getByRole("cell", { name: "orders" })).toBeVisible();
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
});
test("integrations and onboarding remain truthful at a narrow viewport", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/integrations");
  await expect(
    page.getByText(/No supported integration metadata/),
  ).toBeVisible();
  await page.goto("/onboarding");
  await page.getByRole("button", { name: "Continue" }).click();
  await page.getByRole("button", { name: "Continue" }).click();
  await expect(page.getByRole("alert")).toHaveText(/Select at least one/);
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
});
