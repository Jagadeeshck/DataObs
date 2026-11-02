import { describe, expect, it } from "vitest";
import {
  aggregateFacets,
  applyFacetSelections,
  rankAssets,
  toggleSelection,
  tokenise,
} from "./catalog";
import type { Asset } from "../api";

const asset = (overrides: Partial<Asset> & { id: string }): Asset => ({
  name: overrides.id,
  ...overrides,
});

describe("catalog browse groundwork", () => {
  it("tokenises on non-alphanumerics and lowercases", () => {
    expect(tokenise("Orders.Events_v2")).toEqual(["orders", "events", "v2"]);
    expect(tokenise("   ")).toEqual([]);
  });

  it("preserves server order and zero scores for an empty query (browse mode)", () => {
    const input = [asset({ id: "b" }), asset({ id: "a" })];
    const ranked = rankAssets(input, "");
    expect(ranked.map((r) => r.asset.id)).toEqual(["b", "a"]);
    expect(ranked.every((r) => r.score === 0)).toBe(true);
    expect(ranked.every((r) => r.matchedFields.length === 0)).toBe(true);
  });

  it("ranks name matches above unrelated assets and explains matched fields", () => {
    const input = [
      asset({ id: "noise", name: "unrelated table" }),
      asset({ id: "orders", name: "orders events", asset_type: "topic" }),
    ];
    const ranked = rankAssets(input, "orders");
    expect(ranked[0].asset.id).toBe("orders");
    expect(ranked[0].score).toBeGreaterThan(0);
    expect(ranked[0].matchedFields).toContain("name");
    expect(ranked[1].score).toBe(0);
  });

  it("breaks score ties deterministically by name then id", () => {
    const input = [
      asset({ id: "z", name: "same" }),
      asset({ id: "a", name: "same" }),
    ];
    // No query term match -> equal scores -> stable name/id ordering.
    expect(rankAssets(input, "").map((r) => r.asset.id)).toEqual(["z", "a"]);
    expect(rankAssets(input, "same").map((r) => r.asset.id)).toEqual([
      "a",
      "z",
    ]);
  });

  it("aggregates facet counts and omits never-reported dimensions", () => {
    const facets = aggregateFacets([
      asset({ id: "1", asset_type: "table", owner_team: "team-2" }),
      asset({ id: "2", asset_type: "table", owner_team: "team-1" }),
      asset({ id: "3", asset_type: "topic", owner_team: "team-2" }),
    ]);
    const assetType = facets.find((f) => f.dimension === "asset_type");
    expect(assetType?.values).toEqual([
      { value: "table", count: 2 },
      { value: "topic", count: 1 },
    ]);
    // source/health never reported -> dimension absent, not a measured zero.
    expect(facets.some((f) => f.dimension === "source")).toBe(false);
    expect(facets.some((f) => f.dimension === "health")).toBe(false);
  });

  it("filters with AND across dimensions and OR within a dimension", () => {
    const assets = [
      asset({ id: "1", asset_type: "table", owner_team: "team-2" }),
      asset({ id: "2", asset_type: "topic", owner_team: "team-2" }),
      asset({ id: "3", asset_type: "table", owner_team: "team-1" }),
    ];
    const selections = [
      { dimension: "asset_type" as const, value: "table" },
      { dimension: "asset_type" as const, value: "topic" },
      { dimension: "owner_team" as const, value: "team-2" },
    ];
    expect(applyFacetSelections(assets, selections).map((a) => a.id)).toEqual([
      "1",
      "2",
    ]);
    expect(applyFacetSelections(assets, []).map((a) => a.id)).toEqual([
      "1",
      "2",
      "3",
    ]);
  });

  it("toggles a selection on and off", () => {
    const candidate = { dimension: "source" as const, value: "kafka" };
    const added = toggleSelection([], candidate);
    expect(added).toEqual([candidate]);
    expect(toggleSelection(added, candidate)).toEqual([]);
  });
});
