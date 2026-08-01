import { accessToken } from "../auth/oidc";
import { ApiError } from "./common";
import { instrumentedFetch } from "../observability";

const requestId = () => crypto.randomUUID();
export async function read<T>(
  path: string,
  tenant: string,
  signal?: AbortSignal,
): Promise<T> {
  const token = await accessToken();
  const response = await instrumentedFetch(path, {
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
export async function write<T>(
  path: string,
  tenant: string,
  body: unknown,
  signal?: AbortSignal,
  headers: Record<string, string> = {},
): Promise<T> {
  const token = await accessToken();
  const response = await instrumentedFetch(path, {
    method: "POST",
    signal,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      "X-DataObs-Tenant": tenant,
      "X-Request-ID": requestId(),
      ...headers,
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
