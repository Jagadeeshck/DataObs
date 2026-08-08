import type { EntityType } from "../app/entityLinks";
import type { TimeRange } from "../state/context";

export const INVESTIGATION_LIMITS = {
  timeline: 100,
  provider: 25,
  timeoutMs: 2000,
  deadlineMs: 4000,
  pins: 5,
  graphNodes: 50,
  graphEdges: 100,
} as const;
export type EvidenceState =
  | "available"
  | "partial"
  | "stale"
  | "missing"
  | "unknown"
  | "unavailable";
export type EvidenceProvenance =
  | "measured"
  | "observed"
  | "derived"
  | "estimated"
  | "inferred"
  | "user_action"
  | "system_state"
  | "unavailable";
export type ProviderOutcome =
  | "complete"
  | "empty"
  | "partial"
  | "permission_denied"
  | "not_configured"
  | "unsupported"
  | "timed_out"
  | "unavailable"
  | "cancelled";
export interface InvestigationAnchor {
  entityType: EntityType;
  entityId: string;
  label?: string;
  routeId?: string;
  routeParameters?: Record<string, string>;
}
export interface InvestigationRequest {
  anchor: InvestigationAnchor;
  tenant: string;
  environment: string;
  timeRange: TimeRange;
  start: string;
  end: string;
  permissions: readonly string[];
  generation: number;
}
export interface InvestigationEvidence {
  key: string;
  type: string;
  capabilityId: string;
  ownerTeam: `team-${number}`;
  effectiveAt?: string;
  observedAt?: string;
  future?: boolean;
  state: EvidenceState;
  severity?: string;
  title: string;
  summary?: string;
  entityType?: EntityType;
  entityId?: string;
  confidence?: number;
  provenance: EvidenceProvenance;
  routeId?: string;
  routeParameters?: Record<string, string>;
  requestId?: string;
  explanation?: string;
  impactScore?: number;
  truncated?: boolean;
}
export interface RelatedEntity {
  key: string;
  entityType: EntityType;
  entityId: string;
  label?: string;
  relation:
    | "upstream"
    | "downstream"
    | "input"
    | "output"
    | "contains"
    | "produces"
    | "consumes"
    | "affected_by"
    | "associated_incident"
    | "same_pathway";
  routeId?: string;
  routeParameters?: Record<string, string>;
}
export interface ProviderResult {
  evidence: InvestigationEvidence[];
  related?: RelatedEntity[];
  outcome?: ProviderOutcome;
  truncated?: boolean;
  requestId?: string;
}
export interface InvestigationProvider {
  id: string;
  capabilityId: string;
  ownerTeam: `team-${number}`;
  supports: readonly EntityType[];
  requiredPermission?: string;
  maximumEvents: number;
  maximumLookback: TimeRange;
  timeoutMs: number;
  evidenceTypes: readonly string[];
  isAvailable(request: InvestigationRequest): boolean;
  collect(
    request: InvestigationRequest,
    signal: AbortSignal,
  ): Promise<ProviderResult>;
}
export interface ProviderStatus {
  providerId: string;
  outcome: ProviderOutcome;
  count: number;
}
export interface InvestigationSnapshot {
  generation: number;
  loading: boolean;
  evidence: InvestigationEvidence[];
  related: RelatedEntity[];
  providers: ProviderStatus[];
}
