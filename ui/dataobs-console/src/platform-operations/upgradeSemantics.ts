import type {
  CompatibilityEntry,
  CompatibilityState,
  RollbackClassification,
  UpgradeReadiness,
} from "./upgradeTypes";

const labels: Record<string, string> = {
  compatible_but_unvalidated: "Compatible but unvalidated",
  blocked_by_migration: "Blocked by migration",
  blocked_by_configuration: "Blocked by configuration",
  application_only: "Application only",
  not_applicable: "Not applicable",
  no_go: "NO_GO",
};
export const authoritativeLabel = (value?: string) =>
  value
    ? (labels[value.toLowerCase()] ?? value.replaceAll("_", " ").toUpperCase())
    : "Unknown — not supplied";
export const isCompatibilityBlocking = (state: CompatibilityState) =>
  state === "incompatible";
export const isReadinessBlocking = (state?: UpgradeReadiness) =>
  state === "blocked";
export const isRollbackLimited = (state?: RollbackClassification) =>
  state === "blocked_by_migration" ||
  state === "blocked_by_configuration" ||
  state === "application_only" ||
  state === "unvalidated";
export const entryCurrent = (entry: CompatibilityEntry) =>
  entry.exact ??
  entry.version ??
  entry.profile ??
  entry.minimum ??
  "Not supplied";
export const entryTarget = (entry: CompatibilityEntry) =>
  entry.exact ??
  entry.version ??
  entry.profile ??
  (entry.maximum ? `${entry.minimum}–${entry.maximum}` : "Not supplied");
export const predecessorStatus = (
  dimensions?: Record<string, CompatibilityEntry[]>,
) => dimensions?.previous_dataobs?.[0]?.state ?? "unknown";
export const truthfulCompatibility = (
  state: CompatibilityState,
  freshness: "current" | "stale" | "unknown",
) =>
  freshness === "stale"
    ? `Previous result: ${authoritativeLabel(state)}; Evidence: Stale`
    : freshness === "unknown"
      ? `Result: ${authoritativeLabel(state)}; Evidence: Unknown`
      : authoritativeLabel(state);
