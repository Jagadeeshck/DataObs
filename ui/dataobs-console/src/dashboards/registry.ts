import { buildRoutePath } from "../app/routes";
import type { DashboardFilterKey, DashboardWidgetType } from "./types";

export interface WidgetRegistration {
  type: DashboardWidgetType;
  displayName: string;
  capabilityId: string;
  owner: `team-${0 | 1 | 2 | 3 | 4 | 5}`;
  permission: string;
  providerId: string;
  supportedTimeRanges: readonly string[];
  filters: readonly DashboardFilterKey[];
  resultLimit: number;
  refresh: "global" | "slow";
  min: { width: number; height: number };
  max: { width: number; height: number };
  accessibleAlternative: string;
  emptyMessage: string;
  missingMessage: string;
  errorMessage: string;
  detailsRouteId: string;
  investigation: boolean;
}
const entry = (
  type: DashboardWidgetType,
  displayName: string,
  capabilityId: string,
  permission: string,
  owner: WidgetRegistration["owner"],
  detailsRouteId: string,
  providerId = capabilityId,
): WidgetRegistration => ({
  type,
  displayName,
  capabilityId,
  permission,
  owner,
  detailsRouteId,
  providerId,
  supportedTimeRanges: ["1h", "6h", "24h", "7d", "30d"],
  filters: ["severity", "capability", "health"],
  resultLimit: 50,
  refresh: "global",
  min: { width: 2, height: 2 },
  max: { width: 12, height: 8 },
  accessibleAlternative: `${displayName} as text and a bounded table`,
  emptyMessage: "No evidence in this time range.",
  missingMessage: "Required evidence is missing; this is not zero.",
  errorMessage: "This widget could not load independently.",
  investigation: true,
});
const registrations = [
  entry(
    "overall-health",
    "Overall estate health",
    "command-center",
    "assets:read",
    "team-5",
    "command-center",
  ),
  entry(
    "pillar-health",
    "Six-pillar health",
    "command-center",
    "assets:read",
    "team-5",
    "flow",
  ),
  entry(
    "priority-work",
    "Priority work queue",
    "command-center",
    "assets:read",
    "team-5",
    "command-center",
  ),
  entry(
    "source-coverage",
    "Source coverage",
    "command-center",
    "assets:read",
    "team-5",
    "integrations",
  ),
  entry(
    "recent-changes",
    "Recent changes",
    "command-center",
    "assets:read",
    "team-5",
    "flow",
  ),
  entry(
    "quality-state",
    "Data Quality state",
    "data-quality",
    "quality:read",
    "team-2",
    "quality",
  ),
  entry(
    "job-reliability",
    "Job reliability",
    "jobs",
    "jobs:read",
    "team-3",
    "jobs",
  ),
  entry(
    "stream-reliability",
    "Stream reliability",
    "streams",
    "streams:read",
    "team-1",
    "streams-reliability",
  ),
  entry(
    "stream-anomalies",
    "Active stream anomalies",
    "streams",
    "streams:read",
    "team-1",
    "streams-intelligence",
  ),
  entry(
    "retention-risk",
    "Retention risk",
    "streams",
    "streams:read",
    "team-1",
    "streams-intelligence",
  ),
  entry(
    "pathway-health",
    "Pathway health",
    "pathways",
    "lineage:read",
    "team-1",
    "pathways",
  ),
  entry(
    "active-incidents",
    "Active incidents",
    "incidents",
    "incidents:read",
    "team-4",
    "incidents",
  ),
  entry(
    "event-storms",
    "Event Storms",
    "incidents",
    "incidents:read",
    "team-4",
    "event-storms",
  ),
  entry(
    "lineage-changes",
    "Lineage and schema changes",
    "lineage",
    "lineage:read",
    "team-2",
    "lineage",
  ),
  entry(
    "integration-health",
    "Integration health",
    "integrations",
    "integrations:read",
    "team-5",
    "integrations",
  ),
  entry(
    "watchlist",
    "Operational Watchlist",
    "dashboards",
    "console:read",
    "team-5",
    "global-search",
    "watchlist",
  ),
] as const;
export const widgetRegistry = new Map(
  registrations.map((item) => [item.type, Object.freeze(item)]),
);
export const widgetRegistrations: readonly WidgetRegistration[] = registrations;
export function requireWidget(type: string) {
  const value = widgetRegistry.get(type as DashboardWidgetType);
  if (!value) throw new Error(`Unsupported dashboard widget: ${type}`);
  return value;
}
export function widgetDetailsPath(type: DashboardWidgetType) {
  return buildRoutePath(requireWidget(type).detailsRouteId) ?? "/";
}
