import { expect, test } from "@playwright/test";

const sentinelNames = [
  "DATAOBS_CERT_SENTINEL_DB_PASSWORD",
  "DATAOBS_CERT_SENTINEL_KAFKA_SECRET",
  "DATAOBS_CERT_SENTINEL_WEBHOOK_TOKEN",
  "DATAOBS_CERT_SENTINEL_API_KEY",
];

for (const route of ["/", "/assets", "/pathways", "/streams"]) {
  test(`existing route ${route} is bounded and secret-free`, async ({ page }) => {
    const responses: string[] = [];
    page.on("response", async (response) => {
      if (response.request().resourceType() === "xhr") responses.push(await response.text().catch(() => ""));
    });
    await page.goto(route);
    await expect(page.locator("main")).toBeVisible();
    await expect(page.locator("body")).not.toContainText(/DATAOBS_CERT_SENTINEL_/);
    expect(sentinelNames.some((secret) => responses.join("\n").includes(secret))).toBe(false);
  });
}

test("primary navigation is keyboard reachable with visible focus", async ({ page }) => {
  await page.goto("/");
  await page.keyboard.press("Tab");
  await expect(page.locator(":focus")).toBeVisible();
});
