import source from "./QualityRoutes.tsx?raw";
import { describe, expect, it } from "vitest";
describe("canonical Quality route tree", () => {
  it.each([
    "index",
    'path="monitors"',
    'path="monitors/new"',
    'path="monitors/:monitorId"',
  ])("registers %s exactly once", (route) => {
    expect(source.split(route)).toHaveLength(2);
  });
});
