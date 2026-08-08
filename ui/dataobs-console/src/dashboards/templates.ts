import type {
  DashboardDefinition,
  DashboardFilterKey,
  DashboardWidgetType,
} from "./types";
const widgets = (types: DashboardWidgetType[]) =>
  types.map((type, index) => ({
    id: `${type}-${index + 1}`,
    type,
    title: type
      .split("-")
      .map((x) => x[0].toUpperCase() + x.slice(1))
      .join(" "),
    capabilityId: type,
    layout: {
      x: (index % 3) * 4,
      y: Math.floor(index / 3) * 3,
      width: 4,
      height: 3,
    },
    config: {},
  }));
const template = (
  id: string,
  title: string,
  description: string,
  types: DashboardWidgetType[],
): DashboardDefinition =>
  Object.freeze({
    id,
    version: 1,
    title,
    description,
    owner: "system",
    widgets: widgets(types),
    filters: ["severity", "capability", "health"] as DashboardFilterKey[],
  });
export const dashboardTemplates: readonly DashboardDefinition[] = Object.freeze(
  [
    template(
      "estate-overview",
      "Estate Overview",
      "Cross-capability operational posture without inferred health.",
      [
        "overall-health",
        "pillar-health",
        "active-incidents",
        "priority-work",
        "source-coverage",
        "recent-changes",
        "integration-health",
      ],
    ),
    template(
      "data-reliability",
      "Data Reliability",
      "Quality, job reliability and change evidence.",
      ["quality-state", "job-reliability", "priority-work", "lineage-changes"],
    ),
    template(
      "streaming-operations",
      "Streaming Operations",
      "Bounded stream, retention and pathway evidence.",
      [
        "stream-reliability",
        "stream-anomalies",
        "retention-risk",
        "pathway-health",
        "active-incidents",
      ],
    ),
    template(
      "incident-operations",
      "Incident Operations",
      "Incident and Event Storm response evidence.",
      ["active-incidents", "event-storms", "priority-work"],
    ),
    template(
      "change-impact",
      "Change & Impact",
      "Nearby change and incident evidence; temporal proximity is not causality.",
      ["lineage-changes", "recent-changes", "active-incidents"],
    ),
    template(
      "integration-operations",
      "Integration Operations",
      "Configured provider and collection coverage evidence.",
      ["integration-health", "source-coverage", "recent-changes"],
    ),
  ],
);
export const dashboardTemplate = (id: string) =>
  dashboardTemplates.find((x) => x.id === id);
