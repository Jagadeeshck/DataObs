import type { TimeRange } from "../state/context";

export const dashboardWidgetTypes = [
  "overall-health",
  "pillar-health",
  "priority-work",
  "source-coverage",
  "recent-changes",
  "quality-state",
  "job-reliability",
  "stream-reliability",
  "stream-anomalies",
  "retention-risk",
  "pathway-health",
  "active-incidents",
  "event-storms",
  "lineage-changes",
  "integration-health",
  "watchlist",
] as const;
export type DashboardWidgetType = (typeof dashboardWidgetTypes)[number];
export type DashboardFilterKey =
  | "severity"
  | "capability"
  | "health"
  | "evidence"
  | "entityType";
export type SafeDashboardConfig = string | number | boolean | null;
export interface DashboardLayout {
  x: number;
  y: number;
  width: number;
  height: number;
}
export interface DashboardWidgetDefinition {
  id: string;
  type: DashboardWidgetType;
  title: string;
  capabilityId: string;
  layout: DashboardLayout;
  config: Record<string, SafeDashboardConfig>;
}
export interface DashboardDefinition {
  id: string;
  version: 1;
  title: string;
  description: string;
  owner: "system" | "private";
  templateId?: string;
  defaultTimeRange?: TimeRange;
  widgets: DashboardWidgetDefinition[];
  filters: DashboardFilterKey[];
}
export type WidgetLoadState =
  | "loading"
  | "loaded"
  | "empty"
  | "partial"
  | "stale"
  | "missing"
  | "unavailable"
  | "permission_denied"
  | "not_configured"
  | "timeout"
  | "rate_limited"
  | "error";
