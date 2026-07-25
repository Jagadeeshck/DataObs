import { test, expect } from "@playwright/test";

test("Product 360 exposes scoped core workflow surfaces", async ({ page }) => {
  await page.goto("/data-products/seed-product?tab=Members");
  await expect(
    page.getByRole("heading", { name: /seed product/i }),
  ).toBeVisible();
  await expect(page.getByRole("tab", { name: "Members" })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  await page.getByRole("tab", { name: "Dependencies" }).click();
  await expect(
    page.getByRole("heading", { name: "Dependencies" }),
  ).toBeVisible();
  await expect(page.locator("body")).not.toContainText(
    "secret-sentinel-client-key",
  );
});
