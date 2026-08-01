import type { CommandCenter, Topology } from "./types";
import { accessToken } from "../auth/oidc";
const requestId = () => crypto.randomUUID();
export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly requestId?: string,
  ) {
    super(message);
  }
}
async function read<T>(
  path: string,
  tenant: string,
  signal?: AbortSignal,
): Promise<T> {
  const token = await accessToken();
  const response = await fetch(path, {
    signal,
    credentials: "include",
    headers: {
      "X-DataObs-Tenant": tenant,
      "X-Request-ID": requestId(),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(
      body?.error?.message ?? "DataObs API request failed",
      response.status,
      response.headers.get("X-Request-ID") ?? undefined,
    );
  }
  return response.json() as Promise<T>;
}
async function write<T>(
  path: string,
  tenant: string,
  body: unknown,
  signal?: AbortSignal,
): Promise<T> {
  const token = await accessToken();
  const response = await fetch(path, {
    method: "POST",
    signal,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      "X-DataObs-Tenant": tenant,
      "X-Request-ID": requestId(),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
  });
  if (!response.ok)
    throw new ApiError(
      "DataObs API request failed",
      response.status,
      response.headers.get("X-Request-ID") ?? undefined,
    );
  return response.json() as Promise<T>;
}
export const api = {
  jobs: (tenant: string, env: string, search = "", signal?: AbortSignal) =>
    read<{ items: Record<string, unknown>[]; next_cursor: string | null }>(
      `/api/v1/jobs?environment=${encodeURIComponent(env)}&search=${encodeURIComponent(search)}`,
      tenant,
      signal,
    ),
  entity: (
    tenant: string,
    env: string,
    kind: "job" | "run",
    id: string,
    signal?: AbortSignal,
  ) =>
    read<Record<string, unknown>>(
      `/api/v1/${kind}s/${encodeURIComponent(id)}?environment=${encodeURIComponent(env)}`,
      tenant,
      signal,
    ),
  dataProducts: (
    tenant: string,
    env: string,
    query: URLSearchParams,
    signal?: AbortSignal,
  ) =>
    read<DataProductList>(
      `/api/v1/data-products?environment=${encodeURIComponent(env)}&${query}`,
      tenant,
      signal,
    ),
  dataProduct: (
    tenant: string,
    env: string,
    id: string,
    signal?: AbortSignal,
  ) =>
    read<{ product: DataProduct; data_status: string; warnings: string[] }>(
      `/api/v1/data-products/${encodeURIComponent(id)}?environment=${encodeURIComponent(env)}`,
      tenant,
      signal,
    ),
  dataProductSection: (
    tenant: string,
    env: string,
    id: string,
    section: string,
    signal?: AbortSignal,
  ) => {
    const [path, rawQuery = ""] = section.split("?", 2);
    const query = new URLSearchParams(rawQuery);
    query.set("environment", env);
    return read<Record<string, unknown>>(
      `/api/v1/data-products/${encodeURIComponent(id)}/${path}?${query.toString()}`,
      tenant,
      signal,
    );
  },
  streams: (
    tenant: string,
    env: string,
    query: URLSearchParams,
    signal?: AbortSignal,
  ) =>
    read<StreamList>(
      `/api/v1/streams?environment=${encodeURIComponent(env)}&${query}`,
      tenant,
      signal,
    ),
  streamSection: (
    tenant: string,
    env: string,
    root: string,
    id: string,
    section?: string,
    signal?: AbortSignal,
  ) =>
    read<StreamResponse>(
      `/api/v1/${root}/${encodeURIComponent(id)}${section ? `/${section}` : ""}?environment=${encodeURIComponent(env)}`,
      tenant,
      signal,
    ),
  commandCenter: (tenant: string, env: string, signal?: AbortSignal) =>
    read<CommandCenter>(
      `/api/v1/command-center?environment=${encodeURIComponent(env)}`,
      tenant,
      signal,
    ),
  topology: (tenant: string, env: string, signal?: AbortSignal) =>
    read<Topology>(
      `/api/v1/topology?environment=${encodeURIComponent(env)}&max_nodes=1000&max_edges=2500`,
      tenant,
      signal,
    ),
  assets: (
    tenant: string,
    env: string,
    search = "",
    signal?: AbortSignal,
    cursor = "",
    assetType = "",
  ) =>
    read<{
      items: Asset[];
      next_cursor: string | null;
      data_status: string;
      warnings: string[];
    }>(
      `/api/v1/assets?environment=${encodeURIComponent(env)}&search=${encodeURIComponent(search)}&limit=50&cursor=${encodeURIComponent(cursor)}&asset_type=${encodeURIComponent(assetType)}`,
      tenant,
      signal,
    ),
  assetSection: (
    tenant: string,
    env: string,
    id: string,
    section: string,
    signal?: AbortSignal,
  ) =>
    read<Record<string, unknown>>(
      `/api/v1/assets/${encodeURIComponent(id)}/${encodeURIComponent(section)}?environment=${encodeURIComponent(env)}`,
      tenant,
      signal,
    ),
  pathwaySearch: (
    tenant: string,
    env: string,
    request: PathwaySearchRequest,
    signal?: AbortSignal,
  ) =>
    write<PathwaySearchResponse>(
      `/api/v1/pathway-explorer/search?environment=${encodeURIComponent(env)}`,
      tenant,
      request,
      signal,
    ),
};
export interface DataProduct {
  id: string;
  name: string;
  description: string;
  domain: string;
  criticality: string;
  lifecycle_state: string;
  owner: { team: string };
  outputs: Array<{
    entity_id: string;
    entity_type: string;
    display_name: string;
    primary: boolean;
  }>;
  revision: number;
  etag: string;
  updated_at: string;
}
export interface DataProductList {
  items: DataProduct[];
  data_status: string;
  warnings: string[];
  pagination: { limit: number; next_cursor: string | null };
}
export interface StreamItem {
  stream_id?: string;
  topic?: string;
  name?: string;
  cluster_id?: string;
  health?: string;
  maximum_lag?: number;
  retention_risk?: string;
  records_per_second?: number;
  observed_at?: string;
  [key: string]: unknown;
}
export interface StreamList {
  items: StreamItem[];
  next_cursor: string | null;
  data_status: string;
  warnings: string[];
  source_coverage: string[];
}
export interface StreamResponse {
  item?: StreamItem;
  data?: unknown;
  data_status: string;
  warnings: string[];
  missing_inputs: string[];
  observed_at: string;
  confidence?: number;
  source_coverage: string[];
}
export interface Asset {
  id: string;
  name: string;
  fqn?: string;
  asset_type?: string;
  health?: string;
  owner_team?: string;
  business_service?: string;
  source?: string;
  environment?: string;
  last_observed?: string;
}
export interface PathwayNode {
  id: string;
  name: string;
  node_type: string;
}
export interface PathwayEdge {
  id: string;
  source_node_id: string;
  destination_node_id: string;
  health: string;
  evidence: { evidence_type: string; confidence: number };
}
export interface PathwayRoute {
  id: string;
  nodes: PathwayNode[];
  edges: PathwayEdge[];
  complete: boolean;
  confidence: number;
  rank_score: number;
  ranking_explanation: Record<string, number>;
}
export interface PathwaySearchRequest {
  start_node_id: string;
  end_node_id?: string;
  direction: "upstream" | "downstream";
  max_hops: number;
  max_paths: number;
  minimum_confidence: number;
  include_partial: boolean;
  active_only: boolean;
}
export interface PathwaySearchResponse {
  best_path: PathwayRoute | null;
  alternative_paths: PathwayRoute[];
  partial_paths: PathwayRoute[];
  excluded_path_count: number;
  truncated: boolean;
  data_status: string;
  warnings: string[];
}
