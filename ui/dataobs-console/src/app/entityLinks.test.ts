import { describe, expect, it } from "vitest";
import { entityLink } from "./entityLinks";
describe("cross-capability entity links", () => {
  it.each([
    ["incident", "INC/1", "/incidents/INC%2F1"],
    ["monitor", "orders freshness", "/quality/monitors/orders%20freshness"],
    ["topic", "orders.events?v=2", "/streams/topics/orders.events%3Fv%3D2"],
    ["schema_subject", "customers#value", "/streams/schemas/customers%23value"],
  ])("encodes %s identifiers", (type, id, expected) =>
    expect(entityLink(type, id)).toBe(expected),
  );
  it("returns a safe non-link fallback", () => {
    expect(entityLink("secret", "token")).toBeNull();
    expect(entityLink("job", "")).toBeNull();
    expect(entityLink("run", "bad\nvalue")).toBeNull();
  });
});
