/** Shared, absence-preserving Console API contracts. */
export type DataStatus =
  | "complete"
  | "partial"
  | "stale"
  | "not_configured"
  | "unknown"
  | "unavailable";
export interface EvidenceReference {
  id: string;
  source?: string;
  observed_at?: string | null;
}
export interface EvidenceEnvelope {
  data_status: DataStatus;
  observed_at: string;
  source_coverage: string[];
  confidence: number | null;
  warnings: string[];
  missing_inputs: string[];
  request_id: string;
  evidence?: EvidenceReference[];
}
export interface Pagination {
  limit: number;
  offset: number;
  total?: number | null;
}
export interface CursorPage<T> {
  items: T[];
  next_cursor: string | null;
}
export type HealthState = "healthy" | "degraded" | "unhealthy" | "unknown";
export type Permission = string;
export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly requestId?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}
