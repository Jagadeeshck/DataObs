import { describe, expect, it, vi } from "vitest";
import { validateActivityRegistry } from "./registry";
import { classifyAttention } from "./attentionPolicy";
import { mergeActivity } from "./ranking";
import { ActivitySeenStore, MAX_SEEN } from "./localState";
import { safeActivityTelemetry } from "./privacyPolicy";
import type { ActivityItem } from "./types";

const item = (overrides: Partial<ActivityItem> = {}): ActivityItem => ({
  key: "a",
  type: "incident_created",
  capabilityId: "incidents",
  ownerTeam: "team-3",
  occurredAt: "2026-01-01T00:00:00Z",
  severity: "critical",
  state: "active",
  evidenceState: "available",
  title: "sensitive",
  provenance: "observed",
  ...overrides,
});
describe("activity contract", () => {
  it("validates an explicit bounded registry", () =>
    expect(validateActivityRegistry()).toBe(true));
  it("classifies only explicit evidence", () => {
    expect(classifyAttention(item())).toBe("critical");
    expect(
      classifyAttention(item({ capabilityId: "quality" })),
    ).toBeUndefined();
  });
  it("orders deterministically and deduplicates only canonical identity", () =>
    expect(
      mergeActivity([
        item({ key: "b", canonicalEventId: "same" }),
        item({ key: "a", canonicalEventId: "same" }),
        item({ key: "c" }),
      ]).map((x) => x.key),
    ).toEqual(["a", "c"]));
  it("stores only bounded opaque keys scoped to context", () => {
    const values = new Map<string, string>();
    const storage = {
      getItem: (k: string) => values.get(k) ?? null,
      setItem: (k: string, v: string) => values.set(k, v),
      removeItem: (k: string) => values.delete(k),
    };
    const store = new ActivitySeenStore(
      storage,
      vi.fn(() => 100),
    );
    store.mark(
      "tenant-a/env-a",
      Array.from({ length: MAX_SEEN + 2 }, (_, i) => `opaque-${i}`),
    );
    expect(store.read("tenant-a/env-a")).toHaveLength(MAX_SEEN);
    expect(store.read("tenant-b/env-a")).toEqual([]);
    expect(JSON.stringify([...values.values()])).not.toContain("title");
  });
  it("drops business identifiers from telemetry", () =>
    expect(
      safeActivityTelemetry({
        event: "opened",
        activity_id: "secret",
        entity_id: "secret",
        title: "secret",
        capability_id: "incidents",
      }),
    ).toEqual({ event: "opened", capability_id: "incidents" }));
});
