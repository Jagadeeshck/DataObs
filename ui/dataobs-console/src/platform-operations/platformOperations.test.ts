import { describe, expect, it } from "vitest";
import {
  capacityState,
  driftState,
  stateLabel,
  stateTone,
} from "./stateSemantics";
import { lifecycleActions } from "./actions";
import { safeTelemetry } from "./privacy";
describe("platform lifecycle presentation", () => {
  it.each([
    "active",
    "suspended",
    "provisioning",
    "validating",
    "offboarding",
    "deleting",
    "deleted",
    "unknown",
  ])("preserves %s", (state) => {
    expect(stateLabel(state).toLowerCase()).toBe(state);
    expect(stateTone(state)).toBeTruthy();
  });
  it("keeps drift evidence distinct", () => {
    expect(driftState("none")).toBe("no_drift");
    expect(driftState("drift_detected")).toBe("drift_detected");
    expect(driftState("unknown")).toBe("unknown");
    expect(driftState("not_evaluated")).toBe("not_evaluated");
  });
  it.each(["validated", "unvalidated", "unavailable"])(
    "preserves capacity %s",
    (state) => expect(capacityState(state)).toBe(state),
  );
  it("exposes no mutation actions", () =>
    expect(lifecycleActions).toHaveLength(0));
  it("removes private telemetry", () =>
    expect(
      safeTelemetry({
        page_id: "platform",
        tenant_id: "secret",
        resource_label: "secret",
        desired_state: {},
        reason: "secret",
        capacity_state: "unvalidated",
      }),
    ).toEqual({ page_id: "platform", capacity_state: "unvalidated" }));
});
