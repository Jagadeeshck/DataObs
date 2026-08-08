export const activityTypes = [
  "incident_created",
  "incident_updated",
  "incident_resolved",
] as const;
export type ActivityType = (typeof activityTypes)[number];
export type ActivitySeverity =
  | "critical"
  | "high"
  | "medium"
  | "low"
  | "unknown";
export type AttentionCategory =
  | "critical"
  | "action_required"
  | "degraded"
  | "warning";
export type ActivityState =
  | "active"
  | "resolved"
  | "completed"
  | "failed"
  | "waiting"
  | "unknown";
export type EvidenceState =
  | "available"
  | "partial"
  | "stale"
  | "missing"
  | "unavailable";
export type ActivityProvenance =
  | "measured"
  | "observed"
  | "derived"
  | "user_action"
  | "system_transition"
  | "workflow_outcome"
  | "forecast";

export interface ActivityItem {
  key: string;
  canonicalEventId?: string;
  type: ActivityType;
  capabilityId: string;
  ownerTeam: string;
  occurredAt: string;
  observedAt?: string;
  severity?: ActivitySeverity;
  state: ActivityState;
  evidenceState: EvidenceState;
  title: string;
  summary?: string;
  entityType?: string;
  entityId?: string;
  routeId?: string;
  routeParameters?: Record<string, string>;
  provenance: ActivityProvenance;
  attention?: AttentionCategory;
  requestId?: string;
}
export interface ActivityContext {
  tenant: string;
  environment: string;
  permissions: readonly string[];
}
export interface ActivityRequest {
  context: ActivityContext;
  start: string;
  end: string;
  maximumItems: number;
}
export type ProviderOutcome =
  | "available"
  | "partial"
  | "unavailable"
  | "timed_out"
  | "not_configured"
  | "permission_limited";
export interface ActivityProviderResult {
  items: ActivityItem[];
  outcome: ProviderOutcome;
  warning?: string;
}
export interface ActivityProvider {
  id: string;
  capabilityId: string;
  ownerTeam: string;
  requiredPermission?: string;
  maximumItems: number;
  timeoutMs: number;
  maximumLookbackHours: number;
  supportedFilters: readonly string[];
  cursorModel: "none" | "opaque";
  activityTypes: readonly ActivityType[];
  attentionSource: "backend" | "explicit_presentation_mapping";
  supports(context: ActivityContext): boolean;
  load(
    request: ActivityRequest,
    signal: AbortSignal,
  ): Promise<ActivityProviderResult>;
}
