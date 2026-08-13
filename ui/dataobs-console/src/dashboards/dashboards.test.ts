import { describe, expect, it } from "vitest";
import { DashboardQueryCoordinator } from "./controller";
import { adjustLayout } from "./layout";
import { safeDashboardTelemetry } from "./privacyPolicy";
import { requireWidget, widgetRegistrations } from "./registry";
import {
  cloneTemplate,
  parseSavedViews,
  SAVED_VIEW_SCHEMA_VERSION,
} from "./savedViews";
import { dashboardTemplates } from "./templates";
import {
  contextFingerprint,
  WatchlistStore,
  WATCHLIST_LIMIT,
} from "./watchlist";

describe("operational dashboard contracts", () => {
  it("registers unique bounded widgets and rejects unknown types", () => {
    expect(new Set(widgetRegistrations.map((x) => x.type)).size).toBe(
      widgetRegistrations.length,
    );
    expect(
      widgetRegistrations.every(
        (x) => x.resultLimit <= 50 && x.min.width <= x.max.width,
      ),
    ).toBe(true);
    expect(() => requireWidget("javascript")).toThrow(/Unsupported/);
  });
  it("keeps job and incident widget ownership aligned", () => {
    const owners = Object.fromEntries(
      widgetRegistrations.map(({ type, owner }) => [type, owner]),
    );
    expect(owners["job-reliability"]).toBe("team-2");
    expect(owners["active-incidents"]).toBe("team-3");
    expect(owners["event-storms"]).toBe("team-3");
  });
  it("validates all six immutable templates", () => {
    expect(dashboardTemplates).toHaveLength(6);
    expect(
      dashboardTemplates.every(
        (x) =>
          x.owner === "system" && x.widgets.every((w) => requireWidget(w.type)),
      ),
    ).toBe(true);
  });
  it("bounds keyboard layout changes", () => {
    const w = dashboardTemplates[0].widgets[0];
    expect(
      adjustLayout(
        { ...w, layout: { x: 0, y: 0, width: 2, height: 2 } },
        "left",
      ).x,
    ).toBe(0);
    expect(
      adjustLayout(
        { ...w, layout: { x: 0, y: 0, width: 2, height: 2 } },
        "shorter",
      ).height,
    ).toBe(2);
  });
  it("recovers corrupt saved storage and clones presentation only", () => {
    expect(parseSavedViews("bad").views).toEqual([]);
    const view = cloneTemplate("estate-overview", "Operations");
    expect(SAVED_VIEW_SCHEMA_VERSION).toBe(1);
    expect(JSON.stringify(view)).not.toMatch(
      /tenant|environment|entityId|token/i,
    );
  });
  it("deduplicates identical provider work", async () => {
    const q = new DashboardQueryCoordinator();
    let calls = 0;
    const d = {
      providerId: "bounded",
      timeBucket: "24h",
      filters: {},
      refreshGeneration: 1,
      load: async () => ++calls,
    };
    expect(await Promise.all([q.query(d), q.query(d)])).toEqual([1, 1]);
    expect(q.dedupeCount).toBe(1);
  });
  it("only emits approved low-cardinality telemetry", () =>
    expect(
      safeDashboardTelemetry({
        event: "opened",
        template_id: "estate-overview",
        tenant_id: "secret",
        entity_id: "secret",
      }),
    ).toEqual({ event: "opened", template_id: "estate-overview" }));
});
describe("session watchlist", () => {
  it("deduplicates, isolates context and enforces bounds", () => {
    const values = new Map<string, string>();
    const storage = {
      getItem: (k: string) => values.get(k) ?? null,
      setItem: (k: string, v: string) => void values.set(k, v),
      removeItem: (k: string) => void values.delete(k),
    };
    const store = new WatchlistStore(storage);
    const a = contextFingerprint("a", "prod");
    expect(store.add(a, { type: "asset", id: "1", label: "one" })).toHaveLength(
      1,
    );
    expect(store.add(a, { type: "asset", id: "1", label: "one" })).toHaveLength(
      1,
    );
    expect(store.read(contextFingerprint("b", "prod"))).toEqual([]);
    expect(WATCHLIST_LIMIT).toBe(25);
  });
});
