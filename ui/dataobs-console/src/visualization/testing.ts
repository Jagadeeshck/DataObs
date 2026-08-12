import type { TimeSeriesModel, TopologyEdge, TopologyNode } from "./types";
const t = Date.UTC(2026, 0, 1);
export const visualizationFixtures = {
  measuredZero: {
    id: "observed",
    label: "Observed",
    unit: "records",
    points: [
      { time: t, value: 4, kind: "measured" },
      { time: t + 60_000, value: 0, kind: "measured" },
      {
        time: t + 120_000,
        value: null,
        kind: "measured",
        availability: "missing",
      },
    ],
  } satisfies TimeSeriesModel,
  forecast: {
    id: "forecast",
    label: "Forecast",
    unit: "records",
    points: [
      {
        time: t + 180_000,
        value: 5,
        kind: "forecast",
        expectedLower: 3,
        expectedUpper: 7,
      },
    ],
  } satisfies TimeSeriesModel,
  cycleNodes: [
    { id: "a", label: "Dataset A", kind: "dataset" },
    { id: "b", label: "Job B", kind: "job" },
  ] satisfies TopologyNode[],
  cycleEdges: [
    { id: "ab", source: "a", target: "b" },
    { id: "ba", source: "b", target: "a" },
  ] satisfies TopologyEdge[],
};
