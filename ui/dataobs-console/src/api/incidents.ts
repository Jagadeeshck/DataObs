import { read, write } from "./transport";

export type IncidentItem = {
  id: string;
  title: string;
  state: string;
  severity: string;
  owner?: string | null;
  business_service?: string | null;
  affected_assets: string[];
  occurrence_count: number;
  opened_at?: string | null;
  last_observed_at?: string | null;
  data_status: string;
};
export type IncidentDetail = IncidentItem & {
  severity_factors: Record<string, unknown>;
  impact_summary?: string | null;
  first_observed_at?: string | null;
  finding_references: string[];
  latest_evidence: unknown[];
  correlation_key?: string | null;
  revision: string;
  evidence_coverage: string;
  warnings: string[];
  missing_inputs: string[];
  request_id: string;
};
export type TimelineEvent = {
  event_id: string;
  event_type: string;
  timestamp: string;
  actor: string;
  summary: string;
};

export const incidentsApi = {
  list: (
    tenant: string,
    environment: string,
    query: URLSearchParams,
    signal?: AbortSignal,
  ) =>
    read<{
      items: IncidentItem[];
      next_cursor: string | null;
      data_status: string;
      warnings: string[];
    }>(
      `/api/v1/incident-workbench?environment=${encodeURIComponent(environment)}&${query}`,
      tenant,
      signal,
    ),
  detail: (
    tenant: string,
    environment: string,
    id: string,
    signal?: AbortSignal,
  ) =>
    read<IncidentDetail>(
      `/api/v1/incident-workbench/${encodeURIComponent(id)}?environment=${encodeURIComponent(environment)}`,
      tenant,
      signal,
    ),
  timeline: (
    tenant: string,
    environment: string,
    id: string,
    signal?: AbortSignal,
  ) =>
    read<{ items: TimelineEvent[] }>(
      `/api/v1/incident-workbench/${encodeURIComponent(id)}/timeline?environment=${encodeURIComponent(environment)}`,
      tenant,
      signal,
    ),
  mutate: (
    tenant: string,
    environment: string,
    id: string,
    body: Record<string, unknown>,
  ) =>
    write<IncidentDetail>(
      `/api/v1/incident-workbench/${encodeURIComponent(id)}/mutations?environment=${encodeURIComponent(environment)}`,
      tenant,
      body,
    ),
  preview: (
    tenant: string,
    environment: string,
    id: string,
    action_type: string,
  ) =>
    write<Record<string, unknown>>(
      `/api/v1/incident-workbench/${encodeURIComponent(id)}/actions/preview?environment=${encodeURIComponent(environment)}`,
      tenant,
      { action_type, payload: {} },
    ),
};
