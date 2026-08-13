const allowed = new Set([
  "page",
  "compatibility_state",
  "readiness_state",
  "rollback_class",
  "blocker_count_bucket",
  "duration_bucket",
]);
export function upgradeTelemetry(values: Record<string, string | number>) {
  return Object.fromEntries(
    Object.entries(values).filter(([key]) => allowed.has(key)),
  );
}
