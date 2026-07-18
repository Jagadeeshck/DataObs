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
};
