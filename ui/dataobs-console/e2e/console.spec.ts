import { test, expect } from "@playwright/test";
test("Command Center and data flow provide guided investigation", async ({
  page,
}) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: /Good afternoon/ }),
  ).toBeVisible();
  await expect(page.locator(".pillar")).toHaveCount(6);
  await page.getByRole("button", { name: /Explore data flow/ }).click();
  await expect(
    page.getByRole("heading", { name: "Live Data Flow" }),
  ).toBeVisible();
  await page.getByRole("button", { name: /Accessible list/ }).click();
  await expect(
    page.getByRole("heading", { name: "Filtered topology entities" }),
  ).toBeVisible();
});
