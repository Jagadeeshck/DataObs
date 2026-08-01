/** Typed, capability-scoped Connector and Schema 360 client. */
import { read } from "./transport";
import type { CursorPage, EvidenceEnvelope, EvidenceReference } from "./common";

export interface StreamConnector {
  connector_id: string;
  name?: string;
  cluster_id?: string;
  connector_type?: string;
  classification?: string;
  state?: string;
  health?: string;
  reason_codes?: string[];
  task_count?: number | null;
  failed_task_count?: number | null;
  worker_count?: number | null;
  class_fingerprint?: string;
  config_fingerprint?: string;
  observed_at?: string;
  source_coverage?: string[];
}
export interface ConnectorTask {
  task_id: string;
  state?: string;
  worker_id?: string;
  health?: string;
  reason_codes?: string[];
  last_error_category?: string | null;
  last_transition_at?: string | null;
  observed_at?: string;
}
export interface ConnectorChange {
  change_id: string;
  connector_id: string;
  change_type: string;
  previous_fingerprint?: string;
  current_fingerprint?: string;
  observed_at?: string;
  confidence?: number | null;
  evidence_refs?: EvidenceReference[];
}
export interface ConnectorIncident {
  incident_id: string;
  title?: string;
  severity?: string;
  state?: string;
  relationship?: string;
  opened_at?: string;
  observed_at?: string;
}
export interface ConnectorMonitor {
  monitor_id: string;
  name?: string;
  state?: string;
  relationship?: string;
  observed_at?: string;
}
export interface SchemaSubject {
  subject_id: string;
  subject?: string;
  cluster_id?: string;
  registry_id?: string;
  schema_type?: string;
  compatibility?: string;
  latest_version?: number | null;
  versions?: SchemaVersion[];
  references?: unknown[];
  health?: string;
  reason_codes?: string[];
  observed_at?: string;
  source_coverage?: string[];
}
export interface SchemaVersion {
  version: number;
  schema_id?: number | string;
  schema_type?: string;
  fingerprint?: string;
  reference_count?: number | null;
  semantic_summary?: {
    field_count?: number;
    format?: string;
    name?: string | null;
  };
  observed_at?: string;
}
export interface SchemaChange {
  change_id: string;
  from_version?: number;
  to_version?: number;
  classification:
    | "additive"
    | "potentially_breaking"
    | "breaking"
    | "metadata_only"
    | "unknown";
  changed_at?: string;
  confidence?: number | null;
  reason_codes?: string[];
  evidence_refs?: EvidenceReference[];
}
export interface SchemaImpactItem {
  entity_id: string;
  entity_type: string;
  relationship: "direct" | "correlated" | "inferred" | "unknown";
  confidence?: number | null;
  evidence_refs?: EvidenceReference[];
}
export type SchemaIncident = ConnectorIncident;
export type SchemaMonitor = ConnectorMonitor;
export interface Detail<T> extends EvidenceEnvelope {
  item?: T;
  data?: T;
}
export interface List<T> extends EvidenceEnvelope, CursorPage<T> {
  data?: T[];
}

const endpoint = (root: string, id: string, env: string, section?: string) =>
  `/api/v1/${root}/${encodeURIComponent(id)}${section ? `/${section}` : ""}?environment=${encodeURIComponent(env)}`;
const detail = <T>(
  tenant: string,
  env: string,
  root: string,
  id: string,
  section?: string,
  signal?: AbortSignal,
) => read<Detail<T>>(endpoint(root, id, env, section), tenant, signal);
const list = <T>(
  tenant: string,
  env: string,
  root: string,
  id: string,
  section: string,
  signal?: AbortSignal,
) => read<List<T>>(endpoint(root, id, env, section), tenant, signal);
export const streamsApi = {
  connector: (t: string, e: string, id: string, s?: AbortSignal) =>
    detail<StreamConnector>(t, e, "stream-connectors", id, undefined, s),
  connectorTasks: (t: string, e: string, id: string, s?: AbortSignal) =>
    list<ConnectorTask>(t, e, "stream-connectors", id, "tasks", s),
  connectorChanges: (t: string, e: string, id: string, s?: AbortSignal) =>
    list<ConnectorChange>(t, e, "stream-connectors", id, "changes", s),
  connectorIncidents: (t: string, e: string, id: string, s?: AbortSignal) =>
    list<ConnectorIncident>(t, e, "stream-connectors", id, "incidents", s),
  connectorMonitors: (t: string, e: string, id: string, s?: AbortSignal) =>
    list<ConnectorMonitor>(t, e, "stream-connectors", id, "monitors", s),
  connectorEvidence: (t: string, e: string, id: string, s?: AbortSignal) =>
    detail<StreamConnector>(t, e, "stream-connectors", id, "evidence", s),
  schemaSubject: (t: string, e: string, id: string, s?: AbortSignal) =>
    detail<SchemaSubject>(t, e, "schema-subjects", id, undefined, s),
  schemaVersions: (t: string, e: string, id: string, s?: AbortSignal) =>
    list<SchemaVersion>(t, e, "schema-subjects", id, "versions", s),
  schemaChanges: (t: string, e: string, id: string, s?: AbortSignal) =>
    list<SchemaChange>(t, e, "schema-subjects", id, "changes", s),
  schemaImpact: (t: string, e: string, id: string, s?: AbortSignal) =>
    list<SchemaImpactItem>(t, e, "schema-subjects", id, "impact", s),
  schemaIncidents: (t: string, e: string, id: string, s?: AbortSignal) =>
    list<SchemaIncident>(t, e, "schema-subjects", id, "incidents", s),
  schemaMonitors: (t: string, e: string, id: string, s?: AbortSignal) =>
    list<SchemaMonitor>(t, e, "schema-subjects", id, "monitors", s),
  schemaEvidence: (t: string, e: string, id: string, s?: AbortSignal) =>
    detail<SchemaSubject>(t, e, "schema-subjects", id, "evidence", s),
};
