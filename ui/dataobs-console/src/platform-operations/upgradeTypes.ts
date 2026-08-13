export type CompatibilityState =
  | "supported"
  | "compatible_but_unvalidated"
  | "incompatible"
  | "unknown";
export type UpgradeReadiness = "ready" | "warning" | "blocked" | "unknown";
export type RollbackClassification =
  | "supported"
  | "application_only"
  | "blocked_by_migration"
  | "blocked_by_configuration"
  | "not_applicable"
  | "unvalidated";

export interface CompatibilityEntry {
  state: CompatibilityState;
  exact?: string;
  minimum?: string;
  maximum?: string;
  version?: string | null;
  profile?: string;
  evidence?: string;
  reason?: string;
}
export interface CompatibilityResponse {
  dataobs_version: string;
  release_state: string;
  dimensions: Record<string, CompatibilityEntry[]>;
}
export interface UpgradeReadinessResponse {
  current: string;
  target: string;
  readiness: UpgradeReadiness;
  reason_codes: string[];
  rollback_classification: RollbackClassification;
  plan: string[];
}
export interface UpgradeSnapshot {
  compatibility?: CompatibilityResponse;
  readiness?: UpgradeReadinessResponse;
  failures: Array<"compatibility" | "upgrade-readiness">;
}
