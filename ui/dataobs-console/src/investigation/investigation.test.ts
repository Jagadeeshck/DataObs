import { describe, expect, it } from "vitest";
import { investigationPath, parseAnchor, safeConsoleReturn } from "./context";
import { normaliseTimeline } from "./timeline";
import { safeInvestigationTelemetry } from "./privacy";
import { togglePin } from "./session";
import type { InvestigationEvidence } from "./types";

describe("investigation contract", () => {
  it("accepts bounded anchors and rejects malformed values", () => {
    expect(
      parseAnchor(new URLSearchParams("entityType=asset&entityId=a-1"))
        ?.entityId,
    ).toBe("a-1");
    expect(
      parseAnchor(new URLSearchParams("entityType=secret&entityId=x")),
    ).toBeUndefined();
    expect(
      parseAnchor(
        new URLSearchParams(`entityType=asset&entityId=${"x".repeat(513)}`),
      ),
    ).toBeUndefined();
  });
  it("only preserves same-origin known return routes", () => {
    expect(safeConsoleReturn("/search")).toBe("/search");
    expect(safeConsoleReturn("/search?tenant=secret")).toBeUndefined();
    expect(safeConsoleReturn("//evil.example/x")).toBeUndefined();
    expect(safeConsoleReturn("https://evil.example/x")).toBeUndefined();
    expect(
      investigationPath({ entityType: "asset", entityId: "a/b" }),
    ).not.toContain("tenant");
  });
  it("orders deterministically, deduplicates and caps timeline", () => {
    const items = Array.from(
      { length: 105 },
      (_, index): InvestigationEvidence => ({
        key: `k${index}`,
        type: "test",
        capabilityId: index % 2 ? "b" : "a",
        ownerTeam: "team-5",
        effectiveAt: "2026-01-01T00:00:00Z",
        state: "available",
        title: "Evidence",
        provenance: index === 0 ? "estimated" : "measured",
      }),
    );
    items.push(items[0]);
    const result = normaliseTimeline(items);
    expect(result).toHaveLength(100);
    expect(result[0].capabilityId).toBe("a");
    expect(result.some((x) => x.provenance === "estimated")).toBe(true);
  });
  it("preserves measured zero and does not invent confidence", () => {
    const item: InvestigationEvidence = {
      key: "zero",
      type: "metric",
      capabilityId: "quality",
      ownerTeam: "team-4",
      state: "available",
      title: "zero",
      summary: "Observed value 0",
      provenance: "measured",
    };
    expect(item.summary).toContain("0");
    expect(item.confidence).toBeUndefined();
  });
  it("bounds in-memory pins and emits only bounded telemetry", () => {
    let pins: Parameters<typeof togglePin>[0] = [];
    for (let i = 0; i < 7; i++)
      pins = togglePin(pins, { entityType: "asset", entityId: String(i) });
    expect(pins).toHaveLength(5);
    const telemetry = safeInvestigationTelemetry("investigation_opened", {
      anchorType: "asset",
      evidenceCount: 72,
    });
    expect(telemetry).toEqual({
      event: "investigation_opened",
      anchor_type: "asset",
      evidence_count_bucket: "51-100",
    });
    expect(JSON.stringify(telemetry)).not.toContain("tenant");
  });
});
