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

export type TransportResult<T> = {
  data: T;
  etag?: string;
  requestId?: string;
};

/** Shared authenticated transport for capability clients that require OCC metadata. */
export async function request<T>(
  path: string,
  tenant: string,
  options: {
    method?: "GET" | "POST" | "PATCH" | "DELETE";
    body?: unknown;
    signal?: AbortSignal;
    environment?: string;
    ifMatch?: string;
    idempotencyKey?: string;
  } = {},
): Promise<TransportResult<T>> {
  const token = await accessToken();
  const response = await instrumentedFetch(path, {
    method: options.method ?? "GET",
    signal: options.signal,
    credentials: "include",
    headers: {
      ...(options.body === undefined
        ? {}
        : { "Content-Type": "application/json" }),
      "X-DataObs-Tenant": tenant,
      ...(options.environment
        ? { "X-DataObs-Environment": options.environment }
        : {}),
      "X-Request-ID": requestId(),
      ...(options.ifMatch ? { "If-Match": options.ifMatch } : {}),
      ...(options.idempotencyKey
        ? { "Idempotency-Key": options.idempotencyKey }
        : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  });
  const responseRequestId = response.headers.get("X-Request-ID") ?? undefined;
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    const category =
      typeof payload?.error?.code === "string"
        ? payload.error.code
        : response.status === 409 || response.status === 412
          ? "version_conflict"
          : "request_failed";
    throw new ApiError(
      category.replaceAll("_", " "),
      response.status,
      responseRequestId,
    );
  }
  const data =
    response.status === 204 ? (undefined as T) : ((await response.json()) as T);
  return {
    data,
    etag: response.headers.get("ETag") ?? undefined,
    requestId: responseRequestId,
  };
}
