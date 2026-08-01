/** Read-only, capability-scoped client for the Data Quality Console. */
import type {
  CursorPage,
  DataStatus,
  EvidenceEnvelope,
  ApiError,
} from "./common";
import { read } from "./transport";

export type { DataStatus, EvidenceEnvelope, ApiError };
type Evidence<T> = T & EvidenceEnvelope;
type Query =
  | URLSearchParams
  | Record<string, string | number | boolean | null | undefined>;

export interface QualityOverview extends EvidenceEnvelope {
  monitor_count: number;
  enabled_monitor_count: number;
  active_monitor_count: number;
  learning_monitor_count: number;
  degraded_monitor_count: number;
  error_monitor_count: number;
  suppressed_monitor_count: number;
  archived_monitor_count: number;
  stale_monitor_count: number;
  open_finding_count: number | null;
  critical_finding_count: number | null;
  coverage_state: string;
  coverage_numerator: number | null;
  coverage_denominator: number | null;
  coverage_percentage: number | null;
  recommendation_count: number | null;
  high_risk_gap_count: number | null;
  runtime_state: string;
  runtime_backlog: number | null;
  runtime_last_heartbeat: string | null;
  runtime_worker_count: number | null;
  health: string;
  reason_codes: string[];
}
export interface QualityCapability {
  monitor_type: string;
  executable: boolean;
  reason?: string;
}
export interface QualityMonitorSummary {
  id: string;
  name: string;
  monitor_type: string;
  state: string;
  target_type?: string;
  target_display_name: string;
  managed_by: string;
  creation_source: string;
  schedule_interval: string;
  threshold_mode: string;
  severity: string;
  last_observation_at: string | null;
  last_value: number | null;
  unit: string | null;
  last_evaluation_at: string | null;
  last_evaluation_status: string | null;
  anomaly_score: number | null;
  confidence: number | null;
  open_finding_count: number | null;
  highest_open_severity: string | null;
  incident_count: number | null;
  cold_start_state: string | null;
  stale: boolean | null;
  updated_at: string;
  revision: number;
}
export interface QualityMonitor
  extends QualityMonitorSummary, EvidenceEnvelope {
  monitor_version: number;
  threshold: { minimum?: number | null; maximum?: number | null; mode: string };
  baseline?: {
    method: string;
    sensitivity: string;
    seasonality: string[];
  } | null;
  alert?: { consecutive_breaches: number; severity: string };
  target: Record<string, unknown>;
  last_observation?: QualityObservation | null;
  last_evaluation?: QualityEvaluation | null;
  current_baseline?: QualityBaseline | null;
  active_suppression_count?: number | null;
  health: string;
  reason_codes: string[];
}
export interface QualityObservation {
  execution_id: string;
  observed_at: string;
  value: number | null;
  unit: string;
  sample_count: number;
  missing_data: boolean;
  dimensions: Record<string, string>;
  definition_revision: number;
  provider: string;
  source_evidence_refs: string[];
  collection_duration_ms: number;
  trace_id: string | null;
  schema_version: string;
}
export interface QualityEvaluation {
  evaluation_id: string;
  evaluated_at: string;
  actual_value: number | null;
  unit: string | null;
  expected_minimum: number | null;
  expected_maximum: number | null;
  method: string;
  baseline_version: string | null;
  baseline_window: string | null;
  seasonal_cohort: string | null;
  sensitivity: string;
  sample_count: number;
  confidence: number | null;
  cold_start_state: string;
  missing_inputs: string[];
  exclusion_reasons: string[];
  anomaly_score: number | null;
  breached: boolean;
}
export interface QualityBaseline {
  baseline_version: string;
  method: string;
  created_at: string | null;
  sample_count: number | null;
  expected_minimum: number | null;
  expected_maximum: number | null;
  cold_start_state: string | null;
  sensitivity: string | null;
  seasonality: string[];
  definition_revision: number | null;
  active: boolean | null;
}
export interface QualityFinding {
  finding_id: string;
  monitor_id: string;
  monitor_name?: string;
  monitor_type?: string;
  target_display_name?: string;
  evaluation_id: string;
  state: string;
  severity: string;
  incident_id: string | null;
  product_ids: string[];
  definition_revision: number;
  baseline_version: string | null;
  opened_at: string | null;
  updated_at: string | null;
  recovered_at: string | null;
  suppression_state?: string | null;
  relationship: "direct" | "correlated" | "inferred" | "unknown";
}
export interface QualityIncidentRelationship {
  incident_id: string;
  finding_id: string;
  relationship: "direct" | "correlated" | "inferred" | "unknown";
  state?: string;
  severity?: string;
  observed_at?: string | null;
}
export interface QualitySuppression {
  id: string;
  starts_at: string;
  ends_at: string;
  reason: string;
  approved_by: string;
  state: string;
}
export interface QualityDefinitionHistory {
  revision: number;
  action: string;
  actor: string;
  etag: string;
  definition_checksum: string;
  occurred_at: string | null;
}
export interface QualityRecommendation {
  id: string;
  monitor_type: string;
  target_display_name: string;
  rationale: string;
  expected_compute_cost: string;
  expected_collection_permissions: string[];
  confidence: number;
  business_priority: string;
  duplication_analysis: string;
  coverage_gap_closed: string[];
  risk: string;
  state: string;
}
export interface QualityCoverage extends EvidenceEnvelope {
  scope_type?: string;
  scope_id?: string;
  state: string;
  numerator: number | null;
  denominator: number | null;
  coverage_percentage: number | null;
  exclusions: string[];
  by_category: Record<string, string>;
  high_risk_gaps: string[];
  stale_or_broken_monitors: string[];
  recommendation_count: number | null;
}
export interface QualityRuntimeHealth extends EvidenceEnvelope {
  state: string;
  worker_id?: string | null;
  worker_count?: number | null;
  last_heartbeat?: string | null;
  last_successful_cycle?: string | null;
  last_failed_cycle?: string | null;
  backlog?: number | null;
  active_leases?: number | null;
  expired_leases?: number | null;
  consecutive_failures?: number | null;
  next_cycle_at?: string | null;
}
export type QualityRuntimeBacklog = QualityRuntimeHealth;
export type QualityPage<T> = Evidence<CursorPage<T>>;

const params = (environment: string, query?: Query) => {
  const result =
    query instanceof URLSearchParams
      ? new URLSearchParams(query)
      : new URLSearchParams();
  if (query && !(query instanceof URLSearchParams))
    Object.entries(query).forEach(
      ([k, v]) =>
        v !== null && v !== undefined && v !== "" && result.set(k, String(v)),
    );
  result.set("environment", environment);
  return result.toString();
};
const get = <T>(
  path: string,
  tenant: string,
  environment: string,
  query?: Query,
  signal?: AbortSignal,
) => read<T>(`${path}?${params(environment, query)}`, tenant, signal);
const monitorPart = <T>(
  tenant: string,
  env: string,
  id: string,
  part: string,
  query?: Query,
  signal?: AbortSignal,
) =>
  get<QualityPage<T>>(
    `/api/v1/quality/monitors/${encodeURIComponent(id)}/${part}`,
    tenant,
    env,
    query,
    signal,
  );

export const qualityOverview = (t: string, e: string, s?: AbortSignal) =>
  get<QualityOverview>("/api/v1/quality/overview", t, e, undefined, s);
export const qualityCapabilities = (t: string, e: string, s?: AbortSignal) =>
  get<{ items: QualityCapability[] }>(
    "/api/v1/quality/capabilities",
    t,
    e,
    undefined,
    s,
  );
export const qualityMonitors = (
  t: string,
  e: string,
  q?: Query,
  s?: AbortSignal,
) =>
  get<QualityPage<QualityMonitorSummary>>(
    "/api/v1/quality/monitors",
    t,
    e,
    q,
    s,
  );
export const qualityMonitor = (
  t: string,
  e: string,
  id: string,
  s?: AbortSignal,
) =>
  get<QualityMonitor>(
    `/api/v1/quality/monitors/${encodeURIComponent(id)}`,
    t,
    e,
    undefined,
    s,
  );
export const qualityMonitorObservations = (
  t: string,
  e: string,
  id: string,
  q?: Query,
  s?: AbortSignal,
) => monitorPart<QualityObservation>(t, e, id, "observations", q, s);
export const qualityMonitorEvaluations = (
  t: string,
  e: string,
  id: string,
  q?: Query,
  s?: AbortSignal,
) => monitorPart<QualityEvaluation>(t, e, id, "evaluations", q, s);
export const qualityMonitorBaselines = (
  t: string,
  e: string,
  id: string,
  q?: Query,
  s?: AbortSignal,
) => monitorPart<QualityBaseline>(t, e, id, "baselines", q, s);
export const qualityMonitorFindings = (
  t: string,
  e: string,
  id: string,
  q?: Query,
  s?: AbortSignal,
) => monitorPart<QualityFinding>(t, e, id, "findings", q, s);
export const qualityMonitorIncidents = (
  t: string,
  e: string,
  id: string,
  q?: Query,
  s?: AbortSignal,
) => monitorPart<QualityIncidentRelationship>(t, e, id, "incidents", q, s);
export const qualityMonitorSuppressions = (
  t: string,
  e: string,
  id: string,
  q?: Query,
  s?: AbortSignal,
) => monitorPart<QualitySuppression>(t, e, id, "suppressions", q, s);
export const qualityMonitorHistory = (
  t: string,
  e: string,
  id: string,
  q?: Query,
  s?: AbortSignal,
) => monitorPart<QualityDefinitionHistory>(t, e, id, "history", q, s);
export const qualityFindings = (
  t: string,
  e: string,
  q?: Query,
  s?: AbortSignal,
) => get<QualityPage<QualityFinding>>("/api/v1/quality/findings", t, e, q, s);
export const qualityRecommendations = (
  t: string,
  e: string,
  q?: Query,
  s?: AbortSignal,
) =>
  get<QualityPage<QualityRecommendation>>(
    "/api/v1/quality/recommendations",
    t,
    e,
    q,
    s,
  );
export const qualityCoverage = (t: string, e: string, s?: AbortSignal) =>
  get<QualityCoverage>("/api/v1/quality/coverage", t, e, undefined, s);
export const qualityRuntimeHealth = (t: string, e: string, s?: AbortSignal) =>
  get<QualityRuntimeHealth>(
    "/api/v1/quality/runtime/health",
    t,
    e,
    undefined,
    s,
  );
export const qualityRuntimeBacklog = (t: string, e: string, s?: AbortSignal) =>
  get<QualityRuntimeBacklog>(
    "/api/v1/quality/runtime/backlog",
    t,
    e,
    undefined,
    s,
  );
export const qualityApi = {
  qualityOverview,
  qualityCapabilities,
  qualityMonitors,
  qualityMonitor,
  qualityMonitorObservations,
  qualityMonitorEvaluations,
  qualityMonitorBaselines,
  qualityMonitorFindings,
  qualityMonitorIncidents,
  qualityMonitorSuppressions,
  qualityMonitorHistory,
  qualityFindings,
  qualityRecommendations,
  qualityCoverage,
  qualityRuntimeHealth,
  qualityRuntimeBacklog,
};
