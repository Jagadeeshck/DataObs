import { accessToken } from "../auth/oidc";
import { instrumentedFetch } from "../observability";
import { ApiError } from "./common";

export type EvidenceStatus =
  | "available"
  | "partial"
  | "stale"
  | "missing"
  | "unknown"
  | "unavailable"
  | "not_configured";
export interface EvidenceEnvelope {
  data_status: EvidenceStatus;
  observed_at?: string;
  source?: string;
  confidence?: number;
  missing_inputs?: string[];
  warnings?: string[];
}
export interface MonitorCapability {
  monitor_type: string;
  display_name?: string;
  description?: string;
  executable: boolean;
  capability_state: string;
  target_requirements?: string[];
  supported_data_sources?: string[];
  required_parameters?: string[];
  threshold_modes?: string[];
  baseline_support?: boolean;
  provider?: string;
}
export interface MonitorTarget {
  asset_id?: string;
  field_id?: string;
  pathway_id?: string;
  pipeline_id?: string;
  service_id?: string;
  source_type: string;
  connection_ref?: string;
  schema_name?: string;
  table_name?: string;
  columns: string[];
  timestamp_column?: string;
  parameters: Record<string, string>;
}
export interface MonitorSchedule {
  interval: string;
  timezone: string;
  maintenance_windows?: string[];
  business_calendar_exclusions?: string[];
}
export interface ThresholdPolicy {
  mode: string;
  minimum?: number;
  maximum?: number;
  relative_change?: number;
  fixed_safety_minimum?: number;
  fixed_safety_maximum?: number;
}
export interface BaselinePolicy {
  method: string;
  history_points: number;
  minimum_samples: number;
  sensitivity: string;
  seasonality: string[];
}
export interface AlertPolicy {
  severity: string;
  consecutive_breaches: number;
  rca_auto_trigger?: boolean;
}
export interface MonitorDefinition {
  id: string;
  name: string;
  description?: string;
  tenant_id: string;
  environment: string;
  monitor_type: string;
  target: MonitorTarget;
  schedule: MonitorSchedule;
  threshold: ThresholdPolicy;
  baseline?: BaselinePolicy;
  alert: AlertPolicy;
  managed_by: string;
  revision: number;
  etag: string;
  state: string;
  creation_source?: string;
  [key: string]: unknown;
}
export interface Observation {
  execution_id: string;
  monitor_id: string;
  observed_at: string;
  value: number | null;
  missing_data: boolean;
  provider: string;
  source_evidence_refs: string[];
  collection_duration_ms: number;
}
export interface Evaluation {
  evaluation_id: string;
  evaluated_at: string;
  observation: Observation;
  expected_minimum?: number;
  expected_maximum?: number;
  anomaly_score?: number;
  confidence: number;
  cold_start_state: string;
  missing_inputs: string[];
  exclusion_reasons: string[];
  breached: boolean;
}
export interface Finding {
  finding_id: string;
  evaluation_id: string;
  state: string;
  severity: string;
  incident_id?: string;
  product_ids: string[];
}
export interface Recommendation {
  id: string;
  monitor_type: string;
  target: MonitorTarget;
  target_display_name?: string;
  business_priority?: string;
  rationale: string;
  confidence: number;
  expected_compute_cost: string;
  expected_collection_permissions: string[];
  risk: string;
  coverage_gap_closed: string[];
  duplication_analysis: string;
  proposed_baseline?: BaselinePolicy;
  proposed_fixed_safety_threshold?: ThresholdPolicy;
  state: string;
}
export interface Coverage {
  state: string;
  numerator?: number;
  denominator?: number;
  exclusions?: string[];
  by_category?: Record<string, string>;
  high_risk_gaps?: string[];
  stale_or_broken_monitors?: string[];
  recommendation_count?: number;
}
export interface RuntimeHealth {
  state?: string;
  backlog?: number;
  observed_at?: string;
  provider?: string;
  [key: string]: unknown;
}
export interface Suppression {
  id: string;
  starts_at: string;
  ends_at: string;
  reason: string;
  approved_by: string;
}
export interface Page<T> {
  items: T[];
  next_cursor: string | null;
}
export interface ApiResult<T> {
  data: T;
  etag?: string;
  requestId?: string;
}

async function request<T>(
  tenant: string,
  path: string,
  init: RequestInit = {},
): Promise<ApiResult<T>> {
  const token = await accessToken();
  const response = await instrumentedFetch(path, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      "X-DataObs-Tenant": tenant,
      "X-Request-ID": crypto.randomUUID(),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init.headers,
    },
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok)
    throw new ApiError(
      body?.error?.message ?? body?.detail ?? "Data Quality API request failed",
      response.status,
      response.headers.get("X-Request-ID") ?? undefined,
    );
  return {
    data: body as T,
    etag: response.headers.get("ETag") ?? undefined,
    requestId: response.headers.get("X-Request-ID") ?? undefined,
  };
}
const path = (env: string, suffix: string, query?: URLSearchParams) => {
  const q = new URLSearchParams(query);
  q.set("environment", env);
  return `/api/v1/quality${suffix}?${q.toString()}`;
};
export const qualityApi = {
  capabilities: (t: string, e: string, s?: AbortSignal) =>
    request<{ items: MonitorCapability[] }>(t, path(e, "/capabilities"), {
      signal: s,
    }),
  monitors: (t: string, e: string, q: URLSearchParams, s?: AbortSignal) =>
    request<Page<MonitorDefinition>>(t, path(e, "/monitors", q), { signal: s }),
  monitor: (t: string, e: string, id: string, s?: AbortSignal) =>
    request<MonitorDefinition>(
      t,
      path(e, `/monitors/${encodeURIComponent(id)}`),
      { signal: s },
    ),
  create: (
    t: string,
    e: string,
    value: Omit<MonitorDefinition, "revision" | "etag">,
    s?: AbortSignal,
  ) =>
    request<MonitorDefinition>(t, path(e, "/monitors"), {
      method: "POST",
      body: JSON.stringify(value),
      signal: s,
    }),
  section: <T>(
    t: string,
    e: string,
    id: string,
    section: string,
    s?: AbortSignal,
  ) =>
    request<{ items: T[] }>(
      t,
      path(
        e,
        `/monitors/${encodeURIComponent(id)}/${encodeURIComponent(section)}`,
      ),
      { signal: s },
    ),
  coverage: (t: string, e: string, s?: AbortSignal) =>
    request<Coverage>(t, path(e, "/coverage"), { signal: s }),
  runtime: (
    t: string,
    e: string,
    kind: "health" | "backlog",
    s?: AbortSignal,
  ) => request<RuntimeHealth>(t, path(e, `/runtime/${kind}`), { signal: s }),
  recommendations: (t: string, e: string, s?: AbortSignal) =>
    request<{ items: Recommendation[] }>(t, path(e, "/recommendations"), {
      signal: s,
    }),
  mutate: <T>(
    t: string,
    e: string,
    url: string,
    body: unknown,
    headers: Record<string, string> = {},
    s?: AbortSignal,
  ) =>
    request<T>(t, path(e, url), {
      method: "POST",
      body: JSON.stringify(body),
      headers,
      signal: s,
    }),
};
