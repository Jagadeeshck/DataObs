export type SemanticTone =
  | "neutral"
  | "progress"
  | "positive"
  | "caution"
  | "critical";
const progress = new Set([
  "requested",
  "approved",
  "provisioning",
  "configured",
  "validating",
  "installing",
  "migrating",
  "upgrading",
  "rolling_back",
  "draining",
  "retiring",
  "offboarding",
  "deleting",
]);
const positive = new Set([
  "ready",
  "active",
  "registered",
  "no_drift",
  "validated",
]);
const caution = new Set([
  "suspended",
  "maintenance",
  "degraded",
  "retention_hold",
  "unvalidated",
  "not_evaluated",
  "upgrade_pending",
  "rollback_pending",
]);
const critical = new Set(["failed", "drift", "drift_detected", "unavailable"]);
export const stateLabel = (state?: string) =>
  (state || "unknown")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
export function stateTone(state?: string): SemanticTone {
  const value = (state || "unknown").toLowerCase();
  if (progress.has(value)) return "progress";
  if (positive.has(value)) return "positive";
  if (caution.has(value)) return "caution";
  if (critical.has(value)) return "critical";
  return "neutral";
}
export const driftState = (state?: string) => {
  const value = (state || "unknown").toLowerCase().replaceAll(" ", "_");
  if (["none", "in_sync", "no_drift"].includes(value)) return "no_drift";
  if (["drift", "detected", "drift_detected"].includes(value))
    return "drift_detected";
  if (value === "not_evaluated") return value;
  if (value === "unavailable") return value;
  return "unknown";
};
export const capacityState = (state?: string) =>
  ["validated", "unvalidated", "unavailable"].includes(state || "")
    ? state!
    : "unknown";
