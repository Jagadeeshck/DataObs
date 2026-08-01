import { describe, expect, it } from "vitest";
import {
  buildRoutePath,
  consoleRoutes,
  routeForPath,
  visibleRoutes,
} from "./routes";
describe("console route registry", () => {
  it("has unique ids and paths and preserves deep links", () => {
    expect(new Set(consoleRoutes.map((route) => route.id)).size).toBe(
      consoleRoutes.length,
    );
    expect(new Set(consoleRoutes.map((route) => route.path)).size).toBe(
      consoleRoutes.length,
    );
    expect(routeForPath("/streams/topics/orders")?.id).toBe("topic-360");
    expect(routeForPath("/does-not-exist")).toBeUndefined();
  });
  it("does not expose permission-sensitive actions", () => {
    expect(visibleRoutes([]).some((route) => route.id === "integrations")).toBe(
      false,
    );
    expect(
      visibleRoutes(["integrations:read"]).some(
        (route) => route.id === "integrations",
      ),
    ).toBe(true);
  });
  it("keeps router, breadcrumbs, permissions, and detail encoders complete", () => {
    const ids = new Set(consoleRoutes.map(({ id }) => id));
    for (const route of consoleRoutes) {
      expect(route.loader).toBeTypeOf("function");
      if (route.protected) expect(route.requiredPermission).toBeTruthy();
      if (route.parentId) expect(ids.has(route.parentId)).toBe(true);
      if (route.path.includes(":"))
        expect(route.entityParameters?.length).toBeGreaterThan(0);
      if (route.availability === "available")
        expect(route.loader).toBeTypeOf("function");
      if (route.navigation) expect(route.group).not.toBe("System");
    }
    expect(
      buildRoutePath("topic-360", { streamId: "orders/private value" }),
    ).toBe("/streams/topics/orders%2Fprivate%20value");
  });
});
