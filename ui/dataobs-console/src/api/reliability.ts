import { accessToken } from "../auth/oidc";

export type ReliabilityStatus =
  | "healthy"
  | "warning"
  | "breaching"
  | "recovering"
  | "no_data"
  | "stale"
  | "error"
  | "disabled";
export interface ReliabilityDefinition {
  id: string;
  resource_type: string;
  resource_id: string;
  metric: string;
  operator: string;
  threshold: number;
  evaluation_window_seconds: number;
  evaluation_interval_seconds: number;
  required_consecutive_breaches: number;
  recovery_evaluation_count: number;
  missing_data_policy: string;
  enabled: boolean;
  owner: string;
  revision: number;
  latest_evaluation_id?: string | null;
}
export type DefinitionDraft = Omit<
  ReliabilityDefinition,
  "id" | "enabled" | "revision"
>;
export interface CurrentStatus {
  definition_id: string;
  current_status: ReliabilityStatus;
  observed_value: number | null;
  latest_evaluated_at?: string;
  breach_duration_seconds?: number | null;
  consecutive_breaches: number;
  source_coverage?: number | null;
  confidence?: number | null;
  missing_inputs: string[];
}
export interface Evaluation extends CurrentStatus {
  evaluation_id: string;
  previous_status: ReliabilityStatus;
  reason_codes: string[];
  warnings: string[];
  evidence_refs: string[];
}
export interface CursorPage<T> {
  items: T[];
  next_cursor: string | null;
}
export interface RuntimeHealth {
  configured: boolean;
  worker_id: string | null;
  lease_state: string;
  elasticsearch_dependency_state: string;
  definitions_due: number;
  definitions_evaluated: number;
  definitions_skipped: number;
  latest_successful_evaluation: string | null;
  latest_failed_evaluation: string | null;
  consecutive_failures: number;
  checkpoint_status: string;
}
export interface Capabilities {
  resource_types: Array<{ resource_type: string; metrics: string[] }>;
  operators: string[];
  missing_data_policies: string[];
}
export interface EtagResponse<T> {
  value: T;
  etag: string | null;
}
export class ReliabilityApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code?: string,
  ) {
    super(message);
  }
}

async function request<T>(
  tenant: string,
  environment: string,
  path: string,
  init: RequestInit = {},
): Promise<EtagResponse<T>> {
  const token = await accessToken();
  const response = await fetch(path, {
    ...init,
    credentials: "include",
    headers: {
      "X-DataObs-Tenant": tenant,
      "X-DataObs-Environment": environment,
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init.headers,
    },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ReliabilityApiError(
      body?.detail?.message ?? "Reliability request failed",
      response.status,
      body?.detail?.code,
    );
  }
  return {
    value:
      response.status === 204
        ? (undefined as T)
        : ((await response.json()) as T),
    etag: response.headers.get("ETag"),
  };
}
const encode = encodeURIComponent;
export const reliabilityApi = {
  capabilities: (t: string, e: string, signal?: AbortSignal) =>
    request<Capabilities>(t, e, "/api/v1/reliability/capabilities", {
      signal,
    }).then((x) => x.value),
  definitions: (
    t: string,
    e: string,
    query: URLSearchParams,
    signal?: AbortSignal,
  ) =>
    request<CursorPage<ReliabilityDefinition>>(
      t,
      e,
      `/api/v1/stream-slos?${query}`,
      { signal },
    ).then((x) => x.value),
  create: (
    t: string,
    e: string,
    draft: DefinitionDraft,
    key: string,
    signal?: AbortSignal,
  ) =>
    request<ReliabilityDefinition>(t, e, "/api/v1/stream-slos", {
      method: "POST",
      body: JSON.stringify(draft),
      headers: { "Idempotency-Key": key },
      signal,
    }),
  update: (
    t: string,
    e: string,
    id: string,
    patch: Partial<ReliabilityDefinition>,
    etag: string,
    signal?: AbortSignal,
  ) =>
    request<ReliabilityDefinition>(t, e, `/api/v1/stream-slos/${encode(id)}`, {
      method: "PATCH",
      body: JSON.stringify(patch),
      headers: { "If-Match": etag },
      signal,
    }),
  remove: (
    t: string,
    e: string,
    id: string,
    etag: string,
    signal?: AbortSignal,
  ) =>
    request<void>(t, e, `/api/v1/stream-slos/${encode(id)}`, {
      method: "DELETE",
      headers: { "If-Match": etag },
      signal,
    }),
  evaluations: (t: string, e: string, id: string, signal?: AbortSignal) =>
    request<CursorPage<Evaluation>>(
      t,
      e,
      `/api/v1/stream-slos/${encode(id)}/evaluations`,
      { signal },
    ).then((x) => x.value),
  runtime: (t: string, e: string, signal?: AbortSignal) =>
    request<RuntimeHealth>(t, e, "/api/v1/reliability/runtime", {
      signal,
    }).then((x) => x.value),
};
