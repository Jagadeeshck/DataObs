import type { CommandCenter, Topology } from "./types";
import { accessToken } from "../auth/oidc";
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
  const token = await accessToken();
  const response = await fetch(path, {
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
async function write<T>(
  path: string,
  tenant: string,
  body: unknown,
  signal?: AbortSignal,
): Promise<T> {
  const token = await accessToken();
  const response = await fetch(path, {
    method: "POST",
    signal,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      "X-DataObs-Tenant": tenant,
      "X-Request-ID": requestId(),
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
export const api = {
  jobs: (tenant: string, env: string, search = "", signal?: AbortSignal) =>
    read<{ items: Record<string, unknown>[]; next_cursor: string | null }>(
      `/api/v1/jobs?environment=${encodeURIComponent(env)}&search=${encodeURIComponent(search)}`,
      tenant,
      signal,
    ),
  entity: (
    tenant: string,
    env: string,
    kind: "job" | "run",
    id: string,
    signal?: AbortSignal,
  ) =>
    read<Record<string, unknown>>(
      `/api/v1/${kind}s/${encodeURIComponent(id)}?environment=${encodeURIComponent(env)}`,
      tenant,
      signal,
    ),
  dataProducts: (
    tenant: string,
    env: string,
    query: URLSearchParams,
    signal?: AbortSignal,
  ) =>
    read<DataProductList>(
      `/api/v1/data-products?environment=${encodeURIComponent(env)}&${query}`,
      tenant,
      signal,
    ),
  dataProduct: (
    tenant: string,
    env: string,
    id: string,
    signal?: AbortSignal,
  ) =>
    read<{ product: DataProduct; data_status: string; warnings: string[] }>(
      `/api/v1/data-products/${encodeURIComponent(id)}?environment=${encodeURIComponent(env)}`,
      tenant,
      signal,
    ),
  dataProductSection: (
    tenant: string,
    env: string,
    id: string,
    section: string,
    signal?: AbortSignal,
  ) => {
    const [path, rawQuery = ""] = section.split("?", 2);
    const query = new URLSearchParams(rawQuery);
    query.set("environment", env);
    return read<Record<string, unknown>>(
      `/api/v1/data-products/${encodeURIComponent(id)}/${path}?${query.toString()}`,
      tenant,
      signal,
    );
  },
  streams: (
    tenant: string,
    env: string,
    query: URLSearchParams,
    signal?: AbortSignal,
  ) =>
    read<StreamList>(
      `/api/v1/streams?environment=${encodeURIComponent(env)}&${query}`,
      tenant,
      signal,
    ),
  stream: (tenant: string, env: string, id: string, signal?: AbortSignal) =>
    streamRead<StreamItem>(tenant, env, "streams", id, undefined, signal),
  streamPartitions: (
    tenant: string,
    env: string,
    id: string,
    signal?: AbortSignal,
  ) =>
    streamRead<Partition[]>(tenant, env, "streams", id, "partitions", signal),
  streamMetrics: (
    tenant: string,
    env: string,
    id: string,
    signal?: AbortSignal,
  ) => streamRead<StreamMetrics>(tenant, env, "streams", id, "metrics", signal),
  streamThroughput: (
    tenant: string,
    env: string,
    id: string,
    signal?: AbortSignal,
  ) =>
    streamRead<ThroughputSeries>(
      tenant,
      env,
      "streams",
      id,
      "throughput",
      signal,
    ),
  streamConsumerGroups: (
    tenant: string,
    env: string,
    id: string,
    signal?: AbortSignal,
  ) =>
    streamRead<ConsumerGroup[]>(
      tenant,
      env,
      "streams",
      id,
      "consumer-groups",
      signal,
    ),
  streamConfiguration: (
    tenant: string,
    env: string,
    id: string,
    signal?: AbortSignal,
  ) =>
    streamRead<TopicConfiguration>(
      tenant,
      env,
      "streams",
      id,
      "configuration",
      signal,
    ),
  streamPathways: (
    tenant: string,
    env: string,
    id: string,
    signal?: AbortSignal,
  ) =>
    streamRead<PathwaySummary[]>(
      tenant,
      env,
      "streams",
      id,
      "pathways",
      signal,
    ),
  streamIncidents: (
    tenant: string,
    env: string,
    id: string,
    signal?: AbortSignal,
  ) =>
    streamRead<IncidentSummary[]>(
      tenant,
      env,
      "streams",
      id,
      "incidents",
      signal,
    ),
  consumerGroups: (
    tenant: string,
    env: string,
    query: URLSearchParams,
    signal?: AbortSignal,
  ) =>
    read<ConsumerGroupList>(
      `/api/v1/consumer-groups?environment=${encodeURIComponent(env)}&${query}`,
      tenant,
      signal,
    ),
  consumerGroup: (
    tenant: string,
    env: string,
    id: string,
    signal?: AbortSignal,
  ) =>
    streamRead<ConsumerGroup>(
      tenant,
      env,
      "consumer-groups",
      id,
      undefined,
      signal,
    ),
  consumerGroupMembers: (
    tenant: string,
    env: string,
    id: string,
    signal?: AbortSignal,
  ) =>
    streamRead<Member[]>(tenant, env, "consumer-groups", id, "members", signal),
  consumerGroupAssignments: (
    tenant: string,
    env: string,
    id: string,
    signal?: AbortSignal,
  ) =>
    streamRead<Assignment[]>(
      tenant,
      env,
      "consumer-groups",
      id,
      "assignments",
      signal,
    ),
  consumerGroupOffsets: (
    tenant: string,
    env: string,
    id: string,
    signal?: AbortSignal,
  ) =>
    streamRead<Offset[]>(tenant, env, "consumer-groups", id, "offsets", signal),
  consumerGroupLag: (
    tenant: string,
    env: string,
    id: string,
    signal?: AbortSignal,
  ) =>
    streamRead<LagDetails>(tenant, env, "consumer-groups", id, "lag", signal),
  consumerGroupLagHeatmap: (
    tenant: string,
    env: string,
    id: string,
    signal?: AbortSignal,
  ) =>
    streamRead<LagCell[]>(
      tenant,
      env,
      "consumer-groups",
      id,
      "lag-heatmap",
      signal,
    ),
  consumerGroupRetentionRisk: (
    tenant: string,
    env: string,
    id: string,
    signal?: AbortSignal,
  ) =>
    streamRead<RetentionRisk>(
      tenant,
      env,
      "consumer-groups",
      id,
      "retention-risk",
      signal,
    ),
  consumerGroupRebalances: (
    tenant: string,
    env: string,
    id: string,
    signal?: AbortSignal,
  ) =>
    streamRead<Rebalance[]>(
      tenant,
      env,
      "consumer-groups",
      id,
      "rebalances",
      signal,
    ),
  consumerGroupIncidents: (
    tenant: string,
    env: string,
    id: string,
    signal?: AbortSignal,
  ) =>
    streamRead<IncidentSummary[]>(
      tenant,
      env,
      "consumer-groups",
      id,
      "incidents",
      signal,
    ),
  cluster: (tenant: string, env: string, id: string, signal?: AbortSignal) =>
    streamRead<KafkaCluster>(
      tenant,
      env,
      "stream-clusters",
      id,
      undefined,
      signal,
    ),
  clusterBrokers: (
    tenant: string,
    env: string,
    id: string,
    query = new URLSearchParams(),
    signal?: AbortSignal,
  ) => clusterList<KafkaBroker>(tenant, env, id, "brokers", query, signal),
  clusterTopics: (
    tenant: string,
    env: string,
    id: string,
    query = new URLSearchParams(),
    signal?: AbortSignal,
  ) =>
    clusterList<ClusterTopicSummary>(tenant, env, id, "topics", query, signal),
  clusterConsumerGroups: (
    tenant: string,
    env: string,
    id: string,
    query = new URLSearchParams(),
    signal?: AbortSignal,
  ) =>
    clusterList<ClusterConsumerGroupSummary>(
      tenant,
      env,
      id,
      "consumer-groups",
      query,
      signal,
    ),
  clusterConnectors: (
    tenant: string,
    env: string,
    id: string,
    query = new URLSearchParams(),
    signal?: AbortSignal,
  ) =>
    clusterList<ClusterConnectorSummary>(
      tenant,
      env,
      id,
      "connectors",
      query,
      signal,
    ),
  clusterHealth: (
    tenant: string,
    env: string,
    id: string,
    signal?: AbortSignal,
  ) =>
    read<ClusterHealthSummary & EvidenceEnvelope>(
      `/api/v1/stream-clusters/${encodeURIComponent(id)}/health?environment=${encodeURIComponent(env)}`,
      tenant,
      signal,
    ),
  clusterChanges: (
    tenant: string,
    env: string,
    id: string,
    query = new URLSearchParams(),
    signal?: AbortSignal,
  ) => clusterList<ClusterChange>(tenant, env, id, "changes", query, signal),
  clusterIncidents: (
    tenant: string,
    env: string,
    id: string,
    query = new URLSearchParams(),
    signal?: AbortSignal,
  ) =>
    clusterList<IncidentSummary>(tenant, env, id, "incidents", query, signal),
  streamSection: (
    tenant: string,
    env: string,
    root: string,
    id: string,
    section?: string,
    signal?: AbortSignal,
  ) =>
    read<StreamResponse>(
      `/api/v1/${root}/${encodeURIComponent(id)}${section ? `/${section}` : ""}?environment=${encodeURIComponent(env)}`,
      tenant,
      signal,
    ),
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
  assets: (
    tenant: string,
    env: string,
    search = "",
    signal?: AbortSignal,
    cursor = "",
    assetType = "",
  ) =>
    read<{
      items: Asset[];
      next_cursor: string | null;
      data_status: string;
      warnings: string[];
    }>(
      `/api/v1/assets?environment=${encodeURIComponent(env)}&search=${encodeURIComponent(search)}&limit=50&cursor=${encodeURIComponent(cursor)}&asset_type=${encodeURIComponent(assetType)}`,
      tenant,
      signal,
    ),
  assetSection: (
    tenant: string,
    env: string,
    id: string,
    section: string,
    signal?: AbortSignal,
  ) =>
    read<Record<string, unknown>>(
      `/api/v1/assets/${encodeURIComponent(id)}/${encodeURIComponent(section)}?environment=${encodeURIComponent(env)}`,
      tenant,
      signal,
    ),
  pathwaySearch: (
    tenant: string,
    env: string,
    request: PathwaySearchRequest,
    signal?: AbortSignal,
  ) =>
    write<PathwaySearchResponse>(
      `/api/v1/pathway-explorer/search?environment=${encodeURIComponent(env)}`,
      tenant,
      request,
      signal,
    ),
};
export interface DataProduct {
  id: string;
  name: string;
  description: string;
  domain: string;
  criticality: string;
  lifecycle_state: string;
  owner: { team: string };
  outputs: Array<{
    entity_id: string;
    entity_type: string;
    display_name: string;
    primary: boolean;
  }>;
  revision: number;
  etag: string;
  updated_at: string;
}
export interface DataProductList {
  items: DataProduct[];
  data_status: string;
  warnings: string[];
  pagination: { limit: number; next_cursor: string | null };
}
export interface StreamItem {
  stream_id?: string;
  topic?: string;
  name?: string;
  cluster_id?: string;
  health?: string;
  maximum_lag?: number;
  retention_risk?: string;
  records_per_second?: number;
  bytes_per_second?: number;
  partition_count?: number;
  replication_factor?: number;
  producer_rate?: number;
  consumer_rate?: number;
  consumer_group_count?: number;
  cleanup_policy?: string;
  retention_ms?: number | null;
  min_insync_replicas?: number;
  schema_state?: string;
  connector_state?: string;
  reason_codes?: string[];
  source_coverage?: string[];
  observed_at?: string;
}
export type DataStatus =
  | "complete"
  | "partial"
  | "stale"
  | "unknown"
  | "not_configured"
  | "unavailable";
export interface EvidenceEnvelope {
  data_status: DataStatus;
  observed_at: string;
  source_coverage: string[];
  confidence: number | null;
  warnings: string[];
  missing_inputs: string[];
  request_id: string;
}
export interface SectionResponse<T> extends EvidenceEnvelope {
  item?: T;
  data?: T;
  resource_id?: string;
  kind?: string;
}
function streamRead<T>(
  tenant: string,
  env: string,
  root: string,
  id: string,
  section?: string,
  signal?: AbortSignal,
) {
  return read<SectionResponse<T>>(
    `/api/v1/${root}/${encodeURIComponent(id)}${section ? `/${section}` : ""}?environment=${encodeURIComponent(env)}`,
    tenant,
    signal,
  );
}
function clusterList<T>(
  tenant: string,
  env: string,
  id: string,
  section: string,
  query: URLSearchParams,
  signal?: AbortSignal,
) {
  const params = new URLSearchParams(query);
  params.set("environment", env);
  return read<ClusterListResponse<T>>(
    `/api/v1/stream-clusters/${encodeURIComponent(id)}/${section}?${params.toString()}`,
    tenant,
    signal,
  );
}
export interface ClusterListResponse<T> extends EvidenceEnvelope {
  items: T[];
  next_cursor: string | null;
}
export interface KafkaCluster {
  cluster_id: string;
  name?: string;
  health?: string;
  controller_id?: string | number | null;
  broker_count?: number | null;
  topic_count?: number | null;
  partition_count?: number | null;
  consumer_group_count?: number | null;
  connector_count?: number | null;
  reason_codes?: string[];
  observed_at?: string;
  source_coverage?: string[];
}
export interface KafkaBroker {
  broker_id: string;
  cluster_id: string;
  host?: string | null;
  port?: number | null;
  rack?: string | null;
  controller?: boolean | null;
  health?: string;
  reason_codes?: string[];
  observed_at?: string;
  source_coverage?: string[];
}
export type ClusterTopicSummary = StreamItem;
export type ClusterConsumerGroupSummary = ConsumerGroup;
export interface ClusterConnectorSummary {
  connector_id: string;
  name?: string;
  connector_type?: string;
  classification?: string;
  state?: string;
  task_count?: number | null;
  failed_task_count?: number | null;
  worker_count?: number | null;
  observed_at?: string;
  data_status?: DataStatus;
}
export interface ClusterHealthSummary {
  cluster_id: string;
  health: string;
  reason_codes: string[];
  confidence: number | null;
  data_status: DataStatus;
  observed_at?: string;
  source_coverage: string[];
  missing_inputs: string[];
  broker_count: number | null;
  topic_count: number | null;
  partition_count: number | null;
  consumer_group_count: number | null;
  connector_count: number | null;
  healthy_brokers: number | null;
  unhealthy_brokers: number | null;
  under_replicated_partition_count: number | null;
  leaderless_partition_count: number | null;
  offline_replica_count: number | null;
  degraded_topic_count: number | null;
  critical_topic_count: number | null;
  failed_connector_count: number | null;
  stale_resource_count: number | null;
}
export interface ClusterChange {
  observed_at: string;
  resource_type: string;
  resource_id: string;
  change_type: string;
  previous_fingerprint?: string;
  new_fingerprint?: string;
  source?: string;
  confidence?: number | null;
}
export interface Partition {
  partition: number;
  leader?: number | null;
  replicas?: number[];
  isr?: number[];
  under_replicated?: boolean;
  offline_replicas?: number[];
  high_watermark?: number | null;
  maximum_lag?: number | null;
  health?: string;
  observed_at?: string;
  data_status?: DataStatus;
}
export interface MetricSample {
  observed_at: string;
  value: number | null;
}
export interface ThroughputSeries {
  records_per_second?: MetricSample[];
  bytes_per_second?: MetricSample[];
  producer_rate?: MetricSample[];
  consumer_rate?: MetricSample[];
  sample_period_seconds?: number;
}
export interface StreamMetrics {
  producer_rate?: number | null;
  consumer_rate?: number | null;
  maximum_lag?: number | null;
}
export interface ConsumerGroup {
  group_id: string;
  cluster_id?: string;
  state?: string;
  protocol?: string;
  coordinator?: string;
  member_count?: number;
  assigned_partition_count?: number;
  total_lag?: number | null;
  maximum_lag?: number | null;
  lag_velocity?: number | null;
  drain_time?: number | null;
  retention_risk?: string;
  rebalance_count?: number;
  observed_at?: string;
  source_coverage?: string[];
}
export interface ConsumerGroupList extends EvidenceEnvelope {
  items: ConsumerGroup[];
  next_cursor: string | null;
}
export interface Member {
  member_id: string;
  client_id?: string;
  host?: string;
  assigned_topics?: string[];
  assigned_partition_count?: number;
}
export interface Assignment {
  member_id: string;
  topic: string;
  partitions: number[];
}
export interface Offset {
  topic: string;
  partition: number;
  log_start_offset?: number | null;
  committed_offset?: number | null;
  high_watermark?: number | null;
  lag?: number | null;
  data_status?: DataStatus;
  missing_inputs?: string[];
  observed_at?: string;
}
export interface LagCell extends Offset {
  stale?: boolean;
}
export interface LagDetails {
  total_lag?: number | null;
  maximum_lag?: number | null;
  lag_velocity?: number | null;
  drain_time?: number | null;
  by_topic?: Array<{ topic: string; lag: number | null }>;
  by_partition?: LagCell[];
}
export interface RetentionRisk {
  state?: string;
  affected_topics?: string[];
  affected_partitions?: number[];
  estimated_time_remaining?: number | null;
  suspected_data_loss?: boolean;
  calculation_inputs?: string[];
  missing_inputs?: string[];
  confidence?: number | null;
  compacted_only?: boolean;
}
export interface Rebalance {
  observed_at: string;
  previous_state?: string;
  new_state?: string;
  member_change?: number;
  assignment_change?: number;
  reason?: string | null;
  evidence_status?: string;
}
export interface TopicConfiguration {
  cleanup_policy?: string;
  retention_ms?: number | null;
  min_insync_replicas?: number;
  segment_bytes?: number;
  max_message_bytes?: number;
}
export interface PathwaySummary {
  pathway_id: string;
  health?: string;
}
export interface IncidentSummary {
  incident_id: string;
  status?: string;
  state?: string;
  title?: string;
  severity?: string;
  affected_resource?: string;
  opened_at?: string;
  observed_at?: string;
  relationship?: "direct" | "correlated" | "inferred" | "unknown";
}
export interface StreamList {
  items: StreamItem[];
  next_cursor: string | null;
  data_status: string;
  warnings: string[];
  source_coverage: string[];
}
export interface StreamResponse {
  item?: StreamItem;
  data?: unknown;
  data_status: string;
  warnings: string[];
  missing_inputs: string[];
  observed_at: string;
  confidence?: number;
  source_coverage: string[];
}
export interface Asset {
  id: string;
  name: string;
  fqn?: string;
  asset_type?: string;
  health?: string;
  owner_team?: string;
  business_service?: string;
  source?: string;
  environment?: string;
  last_observed?: string;
}
export interface PathwayNode {
  id: string;
  name: string;
  node_type: string;
}
export interface PathwayEdge {
  id: string;
  source_node_id: string;
  destination_node_id: string;
  health: string;
  evidence: { evidence_type: string; confidence: number };
}
export interface PathwayRoute {
  id: string;
  nodes: PathwayNode[];
  edges: PathwayEdge[];
  complete: boolean;
  confidence: number;
  rank_score: number;
  ranking_explanation: Record<string, number>;
}
export interface PathwaySearchRequest {
  start_node_id: string;
  end_node_id?: string;
  direction: "upstream" | "downstream";
  max_hops: number;
  max_paths: number;
  minimum_confidence: number;
  include_partial: boolean;
  active_only: boolean;
}
export interface PathwaySearchResponse {
  best_path: PathwayRoute | null;
  alternative_paths: PathwayRoute[];
  partial_paths: PathwayRoute[];
  excluded_path_count: number;
  truncated: boolean;
  data_status: string;
  warnings: string[];
}
