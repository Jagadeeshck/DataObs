import { describe, expect, it } from "vitest";
import {
  breadcrumbsForPath,
  consoleRoutes,
  matchRoute,
  resolveRouteState,
  routeForPath,
  titleForPath,
  visibleRoutes,
} from "./routes";
describe("authoritative console route manifest", () => {
  it("has one implementation for every unique id and path", () => {
    expect(new Set(consoleRoutes.map((r) => r.id)).size).toBe(
      consoleRoutes.length,
    );
    expect(new Set(consoleRoutes.map((r) => r.path)).size).toBe(
      consoleRoutes.length,
    );
    expect(consoleRoutes.every((r) => Boolean(r.loader))).toBe(true);
    expect(
      consoleRoutes
        .filter((r) => r.path.startsWith("/quality"))
        .map((r) => r.path),
    ).not.toContain("/quality/*");
  });
  it("registers the complete Beta inventory and correct ownership", () => {
    const paths = [
      "/",
      "/flow",
      "/assets",
      "/assets/:assetId",
      "/quality",
      "/quality/monitors",
      "/quality/monitors/new",
      "/quality/monitors/:monitorId",
      "/jobs",
      "/jobs/:jobId",
      "/runs/compare",
      "/runs/:runId",
      "/lineage",
      "/pathways",
      "/pathways/:pathwayId",
      "/streams",
      "/streams/clusters/:clusterId",
      "/streams/topics/:streamId",
      "/streams/consumer-groups/:groupId",
      "/streams/connectors/:connectorId",
      "/streams/schemas/:subjectId",
      "/data-products",
      "/data-products/:productId",
      "/incidents",
      "/incidents/:incidentId",
      "/integrations",
      "/integrations/:integrationId",
      "/onboarding",
    ];
    expect(consoleRoutes.map((r) => r.path)).toEqual(paths);
    expect(
      consoleRoutes
        .filter((r) => r.path.startsWith("/quality"))
        .every((r) => r.owner === "team-2"),
    ).toBe(true);
    expect(
      consoleRoutes.find((r) => r.id === "incidents")?.implementation,
    ).toBe("available");
  });
  it("resolves permission, implementation, and configuration separately", () => {
    const incidents = consoleRoutes.find((r) => r.id === "incidents")!;
    expect(
      resolveRouteState(incidents, [], { incidents: "available" }),
    ).toMatchObject({
      authorised: false,
      implementation: "available",
      configuration: "available",
      actionable: false,
    });
    expect(
      resolveRouteState(incidents, ["incidents:read"], {
        incidents: "not_configured",
      }).actionable,
    ).toBe(false);
    expect(
      resolveRouteState(incidents, ["incidents:read"], {
        incidents: "available",
      }).actionable,
    ).toBe(true);
    expect(resolveRouteState(incidents, ["incidents:read"]).configuration).toBe(
      "unknown",
    );
    expect(visibleRoutes([]).some((r) => r.id === "incidents")).toBe(false);
  });
  it("matches dynamic routes and creates safe metadata", () => {
    expect(routeForPath("/streams/topics/orders%2Eevents")?.id).toBe(
      "streams-topic",
    );
    expect(matchRoute("/assets/:assetId", "/assets/%E0%A4%A")).toBeNull();
    expect(
      breadcrumbsForPath("/quality/monitors/orders%20freshness").map(
        (c) => c.label,
      ),
    ).toEqual(["Data Quality", "Monitors", "orders freshness"]);
    expect(titleForPath("/incidents/INC-123")).toBe(
      "DataObs — Incident INC-123",
    );
    expect(titleForPath("/missing")).toBe("DataObs — Page not found");
  });
  it("keeps auth routes isolated from the product manifest", () => {
    for (const path of ["/login", "/auth/callback", "/logout", "/unauthorised"])
      expect(routeForPath(path)).toBeUndefined();
  });
});
