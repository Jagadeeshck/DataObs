import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import { mockReleaseShell } from "./fixtures/release";
import { expectKeyboardReachable } from "./helpers/keyboard";

const viewports = [
  { name: "320", width: 320, height: 720 },
  { name: "375", width: 375, height: 812 },
  { name: "768", width: 768, height: 1024 },
  { name: "1024", width: 1024, height: 768 },
  { name: "1440", width: 1440, height: 900 },
];

test.beforeEach(async ({ page }) => mockReleaseShell(page));

for (const viewport of viewports) {
  test(`shared release shell is accessible at ${viewport.name}px`, async ({
    page,
  }) => {
    await page.setViewportSize({
      width: viewport.width,
      height: viewport.height,
    });
    await page.goto("/");
    await expect(
      page.getByRole("heading", { name: "Command Center" }),
    ).toBeVisible();
    await expect(page).toHaveTitle(/Command Center.*DataObs/);

    const hasBodyOverflow = await page.evaluate(
      () =>
        document.documentElement.scrollWidth >
        document.documentElement.clientWidth + 1,
    );
    expect(hasBodyOverflow).toBe(false);

    await expectKeyboardReachable(
      page,
      page.getByRole("link", { name: "Skip to content" }),
    );

    if (viewport.width < 768) {
      await page
        .getByRole("button", { name: "Open product navigation" })
        .click();
      await expect(
        page.getByRole("navigation", { name: "Product navigation" }),
      ).toBeVisible();
      await page
        .getByRole("button", { name: "Close product navigation" })
        .click();
    }

    const results = await new AxeBuilder({ page }).analyze();
    expect(
      results.violations.filter((violation) =>
        ["serious", "critical"].includes(violation.impact ?? ""),
      ),
    ).toEqual([]);
  });
}

test("stale and unavailable API responses remain understandable", async ({
  page,
}) => {
  await page.route("**/api/v1/command-center?**", (route) =>
    route.fulfill({
      status: 503,
      json: {
        detail: {
          code: "evidence_unavailable",
          message: "Current evidence is unavailable",
        },
      },
    }),
  );
  await page.goto("/");
  await expect(
    page.getByText("Operational evidence is unavailable.", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("navigation", { name: "Product navigation" }),
  ).toBeVisible();
});

test("route refresh and deep-link recovery keep the authenticated shell", async ({
  page,
}) => {
  await page.goto("/integrations");
  await expect(
    page.getByRole("heading", { name: "Integrations", exact: true }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Integrations", exact: true }),
  ).toBeVisible();

  await page.goto("/missing-release-route");
  await expect(
    page.getByRole("heading", { name: "Page not found" }),
  ).toBeVisible();
  await expect(
    page.getByRole("navigation", { name: "Product navigation" }),
  ).toBeVisible();
});
