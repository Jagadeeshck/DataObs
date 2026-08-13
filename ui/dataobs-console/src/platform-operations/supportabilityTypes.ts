export type SupportabilitySection =
  | "support"
  | "diagnostics"
  | "configuration"
  | "maintenance"
  | "known-issues"
  | "operational-readiness";

export interface SupportView {
  support_profile: string;
  kubernetes_support_state: string;
  elasticsearch_support_state: string;
  oidc_support_state: string;
  ha_profile: string;
  capacity_profile: string;
  evidence_freshness: string;
  known_blockers: string[];
  release_decision: string;
}
export interface DiagnosticCheck {
  id: string;
  state: string;
  severity: string;
  reason_code: string;
  remediation_code: string;
  checked_at?: string;
}
export interface DiagnosticsView {
  state: string;
  checks: DiagnosticCheck[];
}
export interface ConfigurationView {
  schema_version: string;
  fingerprint: string;
  drift_state: string;
  changed_categories: string[];
}
export interface MaintenanceView {
  state: string;
  reason_code: string;
  start: string | null;
  expected_end: string | null;
  operator_note_reference: string | null;
}
export interface KnownIssue {
  issue_id: string;
  title: string;
  affected_versions: string;
  affected_component: string;
  severity: string;
  state: string;
  workaround_reference: string | null;
  fixed_version: string | null;
  owner_team: string;
}
export interface KnownIssuesView {
  items: KnownIssue[];
  count: number;
}
export interface ReadinessCategory {
  category: string;
  state: string;
  evidence: string;
}
export interface ReadinessView {
  state: string;
  categories: ReadinessCategory[];
}
export interface SupportabilitySnapshot {
  support?: SupportView;
  diagnostics?: DiagnosticsView;
  configuration?: ConfigurationView;
  maintenance?: MaintenanceView;
  knownIssues?: KnownIssuesView;
  readiness?: ReadinessView;
  failures: SupportabilitySection[];
}
