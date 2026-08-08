import type { EntityType } from "../app/entityLinks";

export type MatchCategory =
  | "exact_identifier"
  | "exact_label"
  | "prefix_label"
  | "token_match"
  | "provider_ranked";
export type ProviderStatus =
  | "pending"
  | "complete"
  | "empty"
  | "unavailable"
  | "timed_out"
  | "rate_limited"
  | "failed"
  | "cancelled";
export interface SearchContext {
  tenant: string;
  environment: string;
  permissions: readonly string[];
  capabilities?: Record<string, string>;
}
export interface SearchRequest {
  query: string;
  context: SearchContext;
  limit: number;
}
export interface SearchResult {
  key: string;
  entityType: EntityType;
  capabilityId: string;
  ownerTeam: `team-${number}`;
  identifier: string;
  label: string;
  secondaryLabel?: string;
  health?: string;
  observedAt?: string;
  routeId: string;
  routeParameters: Record<string, string>;
  requiredPermission?: string;
  providerId: string;
  match: MatchCategory;
  stale?: boolean;
  warning?: string;
}
export interface SearchProviderResult {
  results: SearchResult[];
  requestId?: string;
}
export interface SearchProvider {
  id: string;
  label: string;
  capabilityId: string;
  ownerTeam: `team-${number}`;
  entityTypes: readonly EntityType[];
  requiredPermission?: string;
  minimumQueryLength: number;
  maximumResults: number;
  timeoutMs: number;
  isAvailable(context: SearchContext): boolean;
  search(
    request: SearchRequest,
    signal: AbortSignal,
  ): Promise<SearchProviderResult>;
}
export interface ProviderOutcome {
  providerId: string;
  label: string;
  status: ProviderStatus;
  resultCount: number;
  durationBucket: "fast" | "normal" | "slow";
  requestId?: string;
}
export interface SearchSnapshot {
  generation: number;
  searching: boolean;
  results: SearchResult[];
  providers: ProviderOutcome[];
}
