import { expect, test } from "@playwright/test";

test("Product 360 exposes API-backed membership and dependency tabs", async ({
  page,
}) => {
  await page.goto("/data-products/demo?tab=Members");
  await expect(page.getByRole("tab", { name: "Members" })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  await expect(page.getByRole("tabpanel")).toContainText(/members|membership/i);
  await page.getByRole("tab", { name: "Dependencies" }).click();
  await expect(page).toHaveURL(/tab=Dependencies/);
});
