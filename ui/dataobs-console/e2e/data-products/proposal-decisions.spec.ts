import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { mockDataProductRelease } from "../fixtures/release";

test.beforeEach(async ({ page }) => mockDataProductRelease(page));

test("Members proposal controls remain accessible", async ({ page }) => {
  await page.goto("/data-products");
  const results = await new AxeBuilder({ page }).analyze();
  expect(
    results.violations.filter((v) =>
      ["serious", "critical"].includes(v.impact ?? ""),
    ),
  ).toEqual([]);
});
