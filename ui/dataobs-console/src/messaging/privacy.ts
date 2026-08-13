const allowed = new Set([
  "provider_type",
  "resource_kind_category",
  "capability_state",
  "chart_type",
  "result_count_bucket",
  "load_duration_bucket",
  "interaction_category",
]);
export function safeMessagingTelemetry(
  attributes: Record<string, unknown>,
): Record<string, unknown> {
  return Object.fromEntries(
    Object.entries(attributes).filter(([key]) => allowed.has(key)),
  );
}
