/** @vitest-environment jsdom */
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { formatMetric, formatObserved } from "./formatters";
import { meaningfulPercentDifference } from "./semantics";
import { Sparkline } from "./Sparkline";
import { VisualizationState } from "./ChartState";
import { visualizationFixtures } from "./testing";
import { visualizationLimits } from "./tokens";
describe("visual evidence semantics", () => {
  it("preserves measured zero and missing", () => {
    expect(formatObserved(0, "records")).toBe("0 records");
    expect(formatObserved(null, "records")).toBe("No observation");
  });
  it("formats deterministic explicit units", () => {
    expect(formatMetric(1240, "msg/s")).toBe("1,240 msg/s");
    expect(formatMetric(215, "ms")).toBe("215 ms");
    expect(formatMetric(2576980378, "bytes")).toBe("2.4 GiB");
  });
  it("does not invent percentage comparisons", () => {
    expect(meaningfulPercentDifference(5, 0)).toBeNull();
    expect(meaningfulPercentDifference(5, 4, false)).toBeNull();
  });
  it("keeps forecast distinct", () => {
    expect(visualizationFixtures.forecast.points[0].kind).toBe("forecast");
    expect(visualizationFixtures.measuredZero.points[1].value).toBe(0);
    expect(visualizationFixtures.measuredZero.points[2].value).toBeNull();
  });
  it("enforces budgets", () =>
    expect(visualizationLimits).toEqual(
      expect.objectContaining({
        timeSeriesPointsPerSeries: 2000,
        topologyNodes: 100,
        topologyEdges: 200,
      }),
    ));
});
describe("components", () => {
  it("provides sparkline summary", () => {
    render(<Sparkline label="Throughput" values={[1, 0, null, 3]} />);
    expect(screen.getByRole("img").getAttribute("aria-label")).toMatch(
      /increasing/,
    );
  });
  it("does not show empty axes for unavailable state", () => {
    render(<VisualizationState state="unavailable" />);
    expect(screen.getByRole("status").textContent).toContain(
      "Visualization unavailable",
    );
  });
});
