import { describe, expect, it } from "vitest";
// @vitest-environment jsdom
import { onboardingStorageKey, redactOnboardingProgress } from "./progress";
describe("onboarding persistence", () => {
  it("persists only non-sensitive progress", () => {
    const progress = redactOnboardingProgress({ step: 2, goals: ["kafka"] });
    localStorage.setItem(onboardingStorageKey, JSON.stringify(progress));
    const saved = localStorage.getItem(onboardingStorageKey) ?? "";
    expect(saved).toContain("kafka");
    expect(saved).not.toMatch(/secret|token|credential/i);
  });
});
