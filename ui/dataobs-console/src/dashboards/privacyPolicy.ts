export const dashboardTelemetryFields = [
  "event",
  "template_id",
  "view_kind",
  "widget_type",
  "load_state",
  "duration_bucket",
  "widget_count_bucket",
  "action",
  "watchlist_count_bucket",
  "handoff_capability",
] as const;
const forbidden =
  /(tenant|environment|token|entity|label|incident_id|job_id|run_id|topic|schema|search|response|custom_name)/i;
export function safeDashboardTelemetry(input: Record<string, unknown>) {
  return Object.fromEntries(
    Object.entries(input).filter(
      ([key, value]) =>
        dashboardTelemetryFields.includes(key as never) &&
        !forbidden.test(key) &&
        ["string", "number", "boolean"].includes(typeof value),
    ),
  );
}
