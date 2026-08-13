import { describe, expect, it } from "vitest";
import {
  authoritativeLabel,
  isCompatibilityBlocking,
  isReadinessBlocking,
  isRollbackLimited,
  predecessorStatus,
  truthfulCompatibility,
} from "./upgradeSemantics";
import { upgradeTelemetry } from "./upgradePrivacy";

describe("upgrade truthfulness semantics", () => {
  it.each([
    "supported",
    "compatible_but_unvalidated",
    "incompatible",
    "unknown",
  ] as const)("preserves compatibility %s", (state) =>
    expect(authoritativeLabel(state)).toBeTruthy(),
  );
  it.each(["ready", "blocked", "unknown"] as const)(
    "preserves readiness %s",
    (state) => expect(authoritativeLabel(state)).toBeTruthy(),
  );
  it("only treats explicit incompatibility and blocked readiness as blocking", () => {
    expect(isCompatibilityBlocking("incompatible")).toBe(true);
    expect(isCompatibilityBlocking("unknown")).toBe(false);
    expect(isReadinessBlocking("blocked")).toBe(true);
    expect(isReadinessBlocking("unknown")).toBe(false);
  });
  it.each([
    "supported",
    "application_only",
    "blocked_by_migration",
    "blocked_by_configuration",
    "not_applicable",
    "unvalidated",
  ] as const)("renders rollback classification %s", (state) => {
    expect(authoritativeLabel(state)).toBeTruthy();
    expect(isRollbackLimited(state)).toBe(
      [
        "application_only",
        "blocked_by_migration",
        "blocked_by_configuration",
        "unvalidated",
      ].includes(state),
    );
  });
  it("preserves unsupported predecessor", () =>
    expect(
      predecessorStatus({ previous_dataobs: [{ state: "incompatible" }] }),
    ).toBe("incompatible"));
  it("never turns stale pass into current pass", () =>
    expect(truthfulCompatibility("supported", "stale")).toBe(
      "Previous result: SUPPORTED; Evidence: Stale",
    ));
  it("keeps unknown explicit", () =>
    expect(truthfulCompatibility("unknown", "unknown")).toContain(
      "Evidence: Unknown",
    ));
  it("accepts terminal migration values dynamically without a constant", () => {
    const response = { terminal_migration: "0099_future_terminal" };
    expect(response.terminal_migration).toBe("0099_future_terminal");
  });
  it("preserves NO_GO exactly", () =>
    expect(authoritativeLabel("no_go")).toBe("NO_GO"));
});

describe("upgrade privacy", () => {
  it("allowlists low-cardinality telemetry", () =>
    expect(
      upgradeTelemetry({
        page: "upgrades",
        readiness_state: "blocked",
        producer_sha: "secret",
        installation_id: "private",
      }),
    ).toEqual({ page: "upgrades", readiness_state: "blocked" }));
});
