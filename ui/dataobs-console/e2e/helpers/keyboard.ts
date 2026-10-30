import { expect, type Locator, type Page } from "@playwright/test";

/**
 * Proves that a control is reachable through sequential keyboard navigation.
 * The bounded loop absorbs browser differences in the initial document focus
 * without programmatically focusing the target or bypassing Tab navigation.
 */
export async function expectKeyboardReachable(
  page: Page,
  target: Locator,
  maxTabs = 4,
) {
  for (let index = 0; index < maxTabs; index += 1) {
    await page.keyboard.press("Tab");
    const isFocused = await target.evaluate(
      (element) => element === document.activeElement,
    );
    if (isFocused) {
      await expect(target).toBeFocused();
      return;
    }
  }
  await expect(target).toBeFocused();
}
