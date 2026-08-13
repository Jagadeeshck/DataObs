const allowed = new Set([
  "page_id",
  "resource_kind",
  "lifecycle_state",
  "action_type",
  "outcome",
  "duration_bucket",
  "result_count_bucket",
  "drift_state",
  "capacity_state",
]);
export function safeTelemetry(attributes: Record<string, unknown>) {
  return Object.fromEntries(
    Object.entries(attributes).filter(([key]) => allowed.has(key)),
  );
}
