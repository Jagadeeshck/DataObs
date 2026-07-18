import type { CommandCenter, Topology } from "./types";
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
  const response = await fetch(path, {
    signal,
    credentials: "include",
    headers: { "X-DataObs-Tenant": tenant, "X-Request-ID": requestId() },
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
export const api = {
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
  assets: (tenant: string, env: string, search = "", signal?: AbortSignal) =>
    read<{ items: Asset[]; data_status: string; warnings: string[] }>(
      `/api/v1/assets?environment=${encodeURIComponent(env)}&search=${encodeURIComponent(search)}&limit=50`,
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
};
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
