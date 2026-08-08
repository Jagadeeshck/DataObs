import { describe, expect, it, vi } from "vitest";
import { SearchController } from "./controller";
import { createRegistry } from "./registry";
import { classifyMatch, deduplicate, rankResults } from "./ranking";
import { safeSearchTelemetry } from "./privacyPolicy";
import type { SearchProvider, SearchResult } from "./types";
const item = (
  id: string,
  match: SearchResult["match"] = "provider_ranked",
): SearchResult => ({
  key: `p:${id}`,
  entityType: "asset",
  capabilityId: "assets",
  ownerTeam: "team-2",
  identifier: id,
  label: id,
  routeId: "asset-360",
  routeParameters: { assetId: id },
  providerId: "p",
  match,
});
const provider = (overrides: Partial<SearchProvider> = {}): SearchProvider => ({
  id: "p",
  label: "Provider",
  capabilityId: "assets",
  ownerTeam: "team-2",
  entityTypes: ["asset"],
  requiredPermission: "assets:read",
  minimumQueryLength: 2,
  maximumResults: 5,
  timeoutMs: 500,
  isAvailable: () => true,
  search: vi.fn(async () => ({ results: [item("one"), item("one")] })),
  ...overrides,
});
describe("search contract", () => {
  it("rejects duplicate provider IDs and unsafe limits", () => {
    expect(() => createRegistry([provider(), provider()])).toThrow();
    expect(() => createRegistry([provider({ maximumResults: 100 })])).toThrow();
  });
  it("orders providers deterministically", () =>
    expect(
      createRegistry([provider({ id: "z" }), provider({ id: "a" })]).map(
        (p) => p.id,
      ),
    ).toEqual(["a", "z"]));
  it("never invokes an unauthorised provider", async () => {
    const p = provider();
    const value = await new SearchController([p]).search("one", {
      tenant: "t",
      environment: "e",
      permissions: [],
    });
    expect(p.search).not.toHaveBeenCalled();
    expect(value.results).toEqual([]);
  });
  it("deduplicates and caps provider results", async () => {
    const value = await new SearchController([provider()]).search("one", {
      tenant: "t",
      environment: "e",
      permissions: ["assets:read"],
    });
    expect(value.results).toHaveLength(1);
  });
  it("isolates provider failure", async () => {
    const bad = provider({
      id: "bad",
      search: vi.fn(async () => {
        throw new Error("secret backend body");
      }),
    });
    const good = provider({ id: "good" });
    const value = await new SearchController([bad, good]).search("one", {
      tenant: "t",
      environment: "e",
      permissions: ["assets:read"],
    });
    expect(value.results).toHaveLength(1);
    expect(value.providers.find((p) => p.providerId === "bad")?.status).toBe(
      "failed",
    );
  });
  it("ranks explainably with stable ties", () => {
    expect(classifyMatch("A", "a", "label")).toBe("exact_identifier");
    expect(
      rankResults([item("z"), item("a", "exact_label")])[0].identifier,
    ).toBe("a");
    expect(deduplicate([item("a"), item("a")])).toHaveLength(1);
  });
  it("redacts sensitive telemetry", () =>
    expect(
      safeSearchTelemetry({
        event: "submitted",
        query_text: "secret",
        result_id: "id",
        tenant_id: "tenant",
      }),
    ).toEqual({ event: "submitted" }));
});
