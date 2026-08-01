import { describe, expect, it, vi } from "vitest";
import { investigationLink, safeReturnRoute } from "./investigation";
describe("investigation context", () => {
  vi.stubGlobal("location", new URL("https://console.example/"));
  it("accepts only same-origin registered return routes", () => {
    expect(safeReturnRoute("/quality?range=1h")).toBe("/quality?range=1h");
    expect(safeReturnRoute("//evil.example/quality")).toBeUndefined();
    expect(safeReturnRoute("https://evil.example/quality")).toBeUndefined();
    expect(safeReturnRoute("/not-a-route")).toBeUndefined();
  });
  it("encodes entity identifiers and bounded safe handoff context", () => {
    expect(
      investigationLink(
        "incident-workbench",
        { incidentId: "INC/42" },
        {
          sourceRoute: "command-center",
          returnRoute: "/",
          selectedTab: "evidence",
        },
      ),
    ).toBe("/incidents/INC%2F42?from=command-center&tab=evidence&returnTo=%2F");
  });
});
