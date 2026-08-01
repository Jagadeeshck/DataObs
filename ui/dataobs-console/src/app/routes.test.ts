import { describe, expect, it } from "vitest";
import { consoleRoutes, routeForPath, visibleRoutes } from "./routes";
describe("console route registry", () => {
  it("has unique ids and paths and preserves deep links", () => {
    expect(new Set(consoleRoutes.map((route) => route.id)).size).toBe(
      consoleRoutes.length,
    );
    expect(new Set(consoleRoutes.map((route) => route.path)).size).toBe(
      consoleRoutes.length,
    );
    expect(routeForPath("/streams/topics/orders")?.id).toBe("streams");
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
});
