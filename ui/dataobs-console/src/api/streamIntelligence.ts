import { request } from "./transport";

export type DetectorState =
  | "normal"
  | "watch"
  | "anomalous"
  | "severe"
  | "recovering"
  | "insufficient_data"
  | "stale"
  | "error"
  | "disabled";
export interface Capability {
  resource_type: string;
  metrics: string[];
}
export interface Capabilities {
  resource_types: Capability[];
  detector_methods: string[];
  directions: string[];
  required_minimum_samples: number;
  elastic_ml_required: boolean;
}
export interface IntelligenceSummary {
  counts: Record<string, number>;
  data_status: string;
}
export interface RuntimeHealth {
  configured: boolean;
  lease_status: string;
  elasticsearch_dependency_state: string;
  data_status: string;
}
export interface CursorPage<T> {
  items: T[];
  next_cursor?: string;
}
export interface DetectorDefinition {
  detector_id: string;
  resource_type: string;
  resource_id: string;
  metric: string;
  method: string;
  state?: DetectorState;
  enabled: boolean;
  revision: number;
}
export interface AnomalyEvaluation {
  evaluation_id: string;
  state: DetectorState;
  observed_value: number | null;
  expected_value: number | null;
  deviation_score: number | null;
  method: string;
  reason_codes: string[];
}
export interface RetentionForecast {
  forecast_id: string;
  state: string;
  current_lag: number;
  estimated_drain_time_seconds: number | null;
  earliest_exhaustion_seconds: number | null;
  missing_inputs: string[];
}
export interface FailureCandidate {
  candidate_id: string;
  classification: "poison_message_candidate";
  confidence: number;
  reason_codes: string[];
}
export interface ChangeOverlay {
  change_type: string;
  summary: string;
  time_distance_seconds: number;
  confidence: number;
}

const path = (suffix: string, environment: string) =>
  `/api/v1/stream-intelligence${suffix}?environment=${encodeURIComponent(environment)}`;
export const streamIntelligenceApi = {
  capabilities: (tenant: string, environment: string, signal?: AbortSignal) =>
    request<Capabilities>(path("/capabilities", environment), tenant, {
      environment,
      signal,
    }).then((x) => x.data),
  summary: (tenant: string, environment: string, signal?: AbortSignal) =>
    request<IntelligenceSummary>(path("/summary", environment), tenant, {
      environment,
      signal,
    }).then((x) => x.data),
  runtime: (tenant: string, environment: string, signal?: AbortSignal) =>
    request<RuntimeHealth>(path("/runtime", environment), tenant, {
      environment,
      signal,
    }).then((x) => x.data),
  createDraft: (
    tenant: string,
    environment: string,
    body: unknown,
    idempotencyKey: string,
    signal?: AbortSignal,
  ) =>
    request<DetectorDefinition>(
      `/api/v1/stream-detectors?environment=${encodeURIComponent(environment)}`,
      tenant,
      { method: "POST", environment, body, idempotencyKey, signal },
    ),
  update: (
    tenant: string,
    environment: string,
    id: string,
    body: unknown,
    ifMatch: string,
    signal?: AbortSignal,
  ) =>
    request<DetectorDefinition>(
      `/api/v1/stream-detectors/${encodeURIComponent(id)}?environment=${encodeURIComponent(environment)}`,
      tenant,
      { method: "PATCH", environment, body, ifMatch, signal },
    ),
};
