import { describe, expect, it } from "vitest";
import { healthLabel, parseContext } from "./filters";
describe("Console context", () => {
  it("rejects unrecognised tenant and environment URL values", () =>
    expect(parseContext("?tenant=evil&environment=secret")).toEqual({
      tenant: "acme-retail",
      environment: "production",
    }));
  it("does not report unknown coverage as healthy", () =>
    expect(healthLabel("unknown")).toBe("Coverage unavailable"));
});
