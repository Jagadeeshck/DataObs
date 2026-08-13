import { describe, expect, it } from "vitest";
import {
  evidenceLabel,
  freshnessPresentation,
  isBlockingState,
} from "./supportabilitySemantics";
import {
  isSafeDisplayKey,
  supportabilityTelemetry,
} from "./supportabilityPrivacy";

describe("supportability truthfulness", () => {
  it.each([
    ["ready", "READY"],
    ["not_ready", "NOT READY"],
    ["partial", "PARTIAL"],
    ["unknown", "UNKNOWN"],
    ["no_go", "NO GO"],
  ])("preserves authoritative %s", (state, label) =>
    expect(evidenceLabel(state)).toBe(label),
  );
  it("does not turn unknown or missing evidence into pass", () => {
    expect(evidenceLabel()).toContain("Unknown");
    expect(evidenceLabel("missing")).toBe("MISSING");
  });
  it("makes stale passing evidence explicit", () =>
    expect(freshnessPresentation("stale")).toBe("Current evidence: Stale"));
  it("only derives blockers from explicit blocking states", () => {
    expect(isBlockingState("no_go")).toBe(true);
    expect(isBlockingState("critical")).toBe(false);
  });
});

describe("supportability privacy", () => {
  it("strips request IDs, fingerprints, text and SHAs from telemetry", () =>
    expect(
      supportabilityTelemetry({
        page_id: "supportability",
        readiness_state: "no_go",
        request_id: "r",
        fingerprint: "f",
        issue_text: "private",
        producer_sha: "abc",
      }),
    ).toEqual({ page_id: "supportability", readiness_state: "no_go" }));
  it.each([
    "secret",
    "access_token",
    "password",
    "credential",
    "private_key",
    "authorization",
    "cookie",
  ])("blocks sensitive key %s", (key) =>
    expect(isSafeDisplayKey(key)).toBe(false),
  );
});
