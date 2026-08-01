import { accessToken } from "../auth/oidc";
import { ApiError, type DataStatus, type HealthState } from "./common";

export interface EvidenceEnvelope {
  data_status: DataStatus;
  observed_at?: string | null;
  source_coverage: string[];
  confidence?: number | null;
  warnings: string[];
  missing_inputs: string[];
  reason_codes?: string[];
  request_id?: string;
}
export interface PathwaySummary extends Partial<EvidenceEnvelope> {
  pathway_id: string;
  name?: string;
  classification: "complete" | "partial";
  health?: HealthState;
  node_ids?: string[];
  edge_ids?: string[];
  node_count?: number;
  edge_count?: number;
  truncated?: boolean;
  excluded_edge_count?: number;
  owner_team?: string;
  business_service?: string;
  last_seen?: string;
}
export interface PathwayNode {
  node_id: string;
  name?: string;
  qualified_name?: string;
  node_type: string;
  health?: HealthState;
  confidence?: number | null;
}
export interface PathwayEdge {
  edge_id: string;
  source_node_id: string;
  destination_node_id: string;
  edge_type: string;
  health?: HealthState;
  confidence?: number | null;
  metrics?: Record<string, number | null>;
  evidence_refs?: string[];
}
export interface PathwayDetail extends PathwaySummary {
  nodes?: PathwayNode[];
  edges?: PathwayEdge[];
  metrics?: Record<string, number | null>;
  impact_links?: ImpactLink[];
}
export interface Topology extends EvidenceEnvelope {
  pathway_id: string;
  node_ids: string[];
  edge_ids: string[];
  nodes: PathwayNode[];
  edges: PathwayEdge[];
}
export interface PathwayHealth extends EvidenceEnvelope {
  pathway_id: string;
  health: HealthState;
}
export interface PathwayLatency extends EvidenceEnvelope {
  pathway_id: string;
  method: "trace_derived" | "edge_estimate" | "unavailable";
  p50_ms: number | null;
  p95_ms: number | null;
  p99_ms: number | null;
  sample_count: number;
  missing_segments: string[];
}
export interface BottleneckCandidate {
  edge_id: string;
  view: string;
  contribution_percentage: number;
  absolute_contribution: number;
  confidence: number | null;
  calculation_method: string;
  health_explanation: string;
  reason_codes?: string[];
}
export interface Bottlenecks extends EvidenceEnvelope {
  items: BottleneckCandidate[];
  root_cause_claimed: false;
}
export interface ImpactLink {
  resource_id: string;
  resource_type: string;
  name?: string;
  classification: "direct" | "correlated" | "inferred" | "unknown";
  active?: boolean;
}
export interface Impact extends EvidenceEnvelope {
  items: ImpactLink[];
  active_incidents: ImpactLink[];
}
export interface ComparisonResult {
  pathway_id: string;
  metric_deltas: Record<string, number>;
  new_edges: string[];
  removed_edges: string[];
  sample_sufficient: boolean;
  confidence: number;
  warnings: string[];
}
export interface PathwaySlo {
  id: string;
  pathway_id: string;
  metric: string;
  objective: number;
  evaluation_window: string;
  owner?: string;
  enabled: boolean;
  revision: number;
  updated_at?: string;
}
export interface CursorResponse<T> extends EvidenceEnvelope {
  items: T[];
  next_cursor: string | null;
}
export interface WithEtag<T> {
  value: T;
  etag: string | null;
}
export type InventoryFilters = {
  search?: string;
  health?: string;
  classification?: string;
  owner_team?: string;
  business_service?: string;
  truncated?: boolean;
  cursor?: string;
  limit?: number;
};

const request = async <T>(
  tenant: string,
  path: string,
  init: RequestInit = {},
): Promise<WithEtag<T>> => {
  const token = await accessToken();
  const response = await fetch(path, {
    ...init,
    credentials: "include",
    headers: {
      "X-DataObs-Tenant": tenant,
      "X-Request-ID": crypto.randomUUID(),
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init.headers,
    },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(
      body?.detail?.message ?? body?.detail ?? "Pathway API request failed",
      response.status,
      response.headers.get("X-Request-ID") ?? undefined,
    );
  }
  return {
    value:
      response.status === 204
        ? (undefined as T)
        : ((await response.json()) as T),
    etag: response.headers.get("ETag"),
  };
};
const url = (
  path: string,
  environment: string,
  values: Record<string, unknown> = {},
) => {
  const p = new URLSearchParams({ environment });
  Object.entries(values).forEach(([k, v]) => {
    if (v !== undefined && v !== "") p.set(k, String(v));
  });
  return `${path}?${p}`;
};
const id = encodeURIComponent;
export const pathwaysApi = {
  inventory: (
    t: string,
    e: string,
    f: InventoryFilters = {},
    s?: AbortSignal,
  ) =>
    request<CursorResponse<PathwaySummary>>(t, url("/api/v1/pathways", e, f), {
      signal: s,
    }).then((x) => x.value),
  detail: (t: string, e: string, p: string, s?: AbortSignal) =>
    request<PathwayDetail>(t, url(`/api/v1/pathways/${id(p)}`, e), {
      signal: s,
    }).then((x) => x.value),
  topology: (t: string, e: string, p: string, s?: AbortSignal) =>
    request<Topology>(t, url(`/api/v1/pathways/${id(p)}/topology`, e), {
      signal: s,
    }).then((x) => x.value),
  health: (t: string, e: string, p: string, s?: AbortSignal) =>
    request<PathwayHealth>(t, url(`/api/v1/pathways/${id(p)}/health`, e), {
      signal: s,
    }).then((x) => x.value),
  latency: (t: string, e: string, p: string, s?: AbortSignal) =>
    request<PathwayLatency>(t, url(`/api/v1/pathways/${id(p)}/latency`, e), {
      signal: s,
    }).then((x) => x.value),
  bottlenecks: (
    t: string,
    e: string,
    p: string,
    view: string,
    s?: AbortSignal,
  ) =>
    request<Bottlenecks>(
      t,
      url(`/api/v1/pathways/${id(p)}/bottlenecks`, e, { view }),
      { signal: s },
    ).then((x) => x.value),
  impact: (t: string, e: string, p: string, s?: AbortSignal) =>
    request<Impact>(t, url(`/api/v1/pathways/${id(p)}/impact`, e), {
      signal: s,
    }).then((x) => x.value),
  compare: (t: string, e: string, p: string, body: unknown, s?: AbortSignal) =>
    request<ComparisonResult>(t, url(`/api/v1/pathways/${id(p)}/compare`, e), {
      method: "POST",
      body: JSON.stringify(body),
      signal: s,
    }).then((x) => x.value),
  slos: (t: string, e: string, p: string, s?: AbortSignal) =>
    request<CursorResponse<PathwaySlo>>(
      t,
      url("/api/v1/pathway-slos", e, { pathway_id: p }),
      { signal: s },
    ).then((x) => x.value),
  createSlo: (t: string, e: string, body: unknown, s?: AbortSignal) =>
    request<PathwaySlo>(t, url("/api/v1/pathway-slos", e), {
      method: "POST",
      body: JSON.stringify(body),
      signal: s,
    }),
  updateSlo: (
    t: string,
    e: string,
    slo: string,
    body: unknown,
    etag: string,
    signal?: AbortSignal,
  ) =>
    request<PathwaySlo>(t, url(`/api/v1/pathway-slos/${id(slo)}`, e), {
      method: "PATCH",
      headers: { "If-Match": etag },
      body: JSON.stringify(body),
      signal,
    }),
  deleteSlo: (
    t: string,
    e: string,
    slo: string,
    etag: string,
    signal?: AbortSignal,
  ) =>
    request<void>(t, url(`/api/v1/pathway-slos/${id(slo)}`, e), {
      method: "DELETE",
      headers: { "If-Match": etag },
      signal,
    }),
};
