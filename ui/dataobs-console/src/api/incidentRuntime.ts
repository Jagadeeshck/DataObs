import { read } from "./transport";

export type EventStorm = {
  flood_id: string;
  correlation_group_id: string;
  state: string;
  representative_incident_id: string;
  event_count: number;
  event_rate: number;
  incident_count: number;
  occurrence_count: number;
  unique_assets: number;
  data_product_ids: string[];
  business_services: string[];
  first_observed_at?: string;
  last_observed_at?: string;
  suppressed_notification_count: number;
  highest_severity: string;
  notification_decision: string;
  data_status: string;
};
export type CorrelationGroup = {
  group_id: string;
  representative_incident_id: string;
  member_count: number;
  member_sample: string[];
  members_truncated: boolean;
  occurrence_count: number;
  severity: string;
  confidence: number;
  evidence_coverage: number;
  reason_codes: string[];
  policy_name: string;
  policy_version: string;
  policy_hash: string;
  flood_state: string;
  wording: string;
  affected_assets: string[];
  data_product_ids: string[];
  business_services: string[];
};
const scoped = (path: string, environment: string) =>
  `${path}${path.includes("?") ? "&" : "?"}environment=${encodeURIComponent(environment)}`;
export const incidentRuntimeApi = {
  storms: (
    tenant: string,
    environment: string,
    query: URLSearchParams,
    signal?: AbortSignal,
  ) =>
    read<{
      items: EventStorm[];
      next_cursor: string | null;
      data_status: string;
      warnings: string[];
    }>(scoped(`/api/v1/incident-floods?${query}`, environment), tenant, signal),
  storm: (
    tenant: string,
    environment: string,
    id: string,
    signal?: AbortSignal,
  ) =>
    read<EventStorm>(
      scoped(`/api/v1/incident-floods/${encodeURIComponent(id)}`, environment),
      tenant,
      signal,
    ),
  timeline: (
    tenant: string,
    environment: string,
    id: string,
    signal?: AbortSignal,
  ) =>
    read<{
      items: {
        event_id: string;
        timestamp: string;
        state: string;
        action: string;
        reason_codes: string[];
      }[];
    }>(
      scoped(
        `/api/v1/incident-floods/${encodeURIComponent(id)}/timeline`,
        environment,
      ),
      tenant,
      signal,
    ),
  group: (
    tenant: string,
    environment: string,
    id: string,
    signal?: AbortSignal,
  ) =>
    read<CorrelationGroup>(
      scoped(
        `/api/v1/incident-correlation/groups/${encodeURIComponent(id)}`,
        environment,
      ),
      tenant,
      signal,
    ),
  decisions: (
    tenant: string,
    environment: string,
    id: string,
    signal?: AbortSignal,
  ) =>
    read<{
      items: {
        decision_id: string;
        incident_id: string;
        action: string;
        reason_codes: string[];
        wording: string;
      }[];
    }>(
      scoped(
        `/api/v1/incident-correlation/groups/${encodeURIComponent(id)}/decisions`,
        environment,
      ),
      tenant,
      signal,
    ),
};
