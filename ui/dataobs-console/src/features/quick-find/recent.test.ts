// @vitest-environment jsdom
import { beforeEach, describe, expect, it } from "vitest";
import { readRecent, recordRecent } from "./recent";
describe("recent Quick Find items", () => {
  beforeEach(() => sessionStorage.clear());
  it("isolates safe metadata by tenant and environment", () => {
    recordRecent({
      entityType: "topic",
      label: "orders",
      route: "/streams/topics/orders",
      lastViewed: Date.now(),
      tenant: "a",
      environment: "prod",
    });
    expect(readRecent("a", "prod")).toHaveLength(1);
    expect(readRecent("b", "prod")).toEqual([]);
    expect(readRecent("a", "dev")).toEqual([]);
  });
});
