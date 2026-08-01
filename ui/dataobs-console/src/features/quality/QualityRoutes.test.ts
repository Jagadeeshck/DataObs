import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
const source = readFileSync(
  new URL("./QualityRoutes.tsx", import.meta.url),
  "utf8",
);
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
