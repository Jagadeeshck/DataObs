const ALLOWED_TELEMETRY = new Set([
  "page_id",
  "readiness_state",
  "gate_state_category",
  "blocker_count_bucket",
  "known_issue_severity_category",
  "runbook_coverage_bucket",
  "diagnostics_availability",
  "render_duration_bucket",
  "action_category",
  "failed_section_category",
]);
const SENSITIVE_KEY =
  /(secret|token|password|credential|private_key|authorization|cookie|fingerprint|request_id|sha)/i;

export function supportabilityTelemetry(input: Record<string, unknown>) {
  return Object.fromEntries(
    Object.entries(input).filter(
      ([key]) => ALLOWED_TELEMETRY.has(key) && !SENSITIVE_KEY.test(key),
    ),
  );
}

export function isSafeDisplayKey(key: string): boolean {
  return !SENSITIVE_KEY.test(key);
}
