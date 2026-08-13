import { describe, expect, it } from "vitest";
import {
  breadcrumbsForPath,
  consoleRoutes,
  consoleWorkspaces,
  safeParentPath,
  validateNavigationRegistry,
  visibleWorkspaces,
} from "./routes";

describe("Team 5 workspace navigation contract", () => {
  it("keeps the authoritative registry valid and primary navigation bounded", () => {
    expect(validateNavigationRegistry()).toEqual([]);
    expect(consoleWorkspaces).toHaveLength(6);
    expect(consoleWorkspaces.length).toBeLessThanOrEqual(8);
    expect(consoleRoutes.every((route) => route.workspace)).toBe(true);
  });

  it("builds arbitrary workspace and route breadcrumb ancestry", () => {
    expect(
      breadcrumbsForPath("/streams/topics/orders").map(({ label }) => label),
    ).toEqual(["Observe", "Messaging", "orders"]);
    expect(
      breadcrumbsForPath("/incidents/event-storms/storm-1").map(
        ({ label }) => label,
      ),
    ).toEqual(["Respond", "Incidents", "Event Storms", "storm-1"]);
  });

  it("returns stale context details to their nearest static parent", () => {
    expect(
      safeParentPath(consoleRoutes.find(({ id }) => id === "topic-360")!),
    ).toBe("/streams");
    expect(
      safeParentPath(consoleRoutes.find(({ id }) => id === "monitor-360")!),
    ).toBe("/quality/monitors");
  });

  it("does not leak permission-only workspaces", () => {
    expect(visibleWorkspaces([]).map(({ id }) => id)).not.toContain("respond");
    expect(visibleWorkspaces(["incidents:read"]).map(({ id }) => id)).toContain(
      "respond",
    );
  });
});
