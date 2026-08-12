export type EvidenceKind = "measured" | "estimated" | "inferred" | "forecast";
export type EvidenceAvailability =
  | "available"
  | "partial"
  | "stale"
  | "missing"
  | "unknown"
  | "unavailable";
export type HealthState = "healthy" | "warning" | "critical" | "unknown";
export type VisualizationStateKind =
  | "loading"
  | "empty"
  | "partial"
  | "stale"
  | "unavailable"
  | "permission_denied"
  | "not_configured"
  | "error"
  | "rate_limited";
export type MetricUnit =
  | "count"
  | "percent"
  | "bytes"
  | "ms"
  | "seconds"
  | "msg/s"
  | "events/s"
  | "rows/s"
  | "records"
  | "score";
export interface TimePoint {
  time: number;
  value: number | null;
  kind: EvidenceKind;
  availability?: EvidenceAvailability;
  expectedLower?: number;
  expectedUpper?: number;
}
export interface TimeSeriesModel {
  id: string;
  label: string;
  unit: MetricUnit;
  points: readonly TimePoint[];
}
export interface Threshold {
  value: number;
  label: string;
  severity?: HealthState;
}
export interface AnomalyEvidence {
  time: number;
  score?: number;
  detector?: string;
  reason?: string;
  baselineGeneration?: string;
  severity?: HealthState;
}
export type ChangeKind =
  | "schema"
  | "lineage"
  | "configuration"
  | "incident"
  | "deployment"
  | "workflow"
  | "remediation";
export interface ChangeAnnotation {
  id: string;
  time: number;
  kind: ChangeKind;
  label: string;
  source?: string;
  authoritativeCausality?: boolean;
}
export type TopologyNodeKind =
  | "dataset"
  | "table"
  | "file"
  | "job"
  | "run"
  | "stream"
  | "queue"
  | "subscription"
  | "producer"
  | "consumer"
  | "integration"
  | "incident"
  | "monitor"
  | "data-product";
export interface TopologyNode {
  id: string;
  label: string;
  kind: TopologyNodeKind;
  health?: HealthState;
  provider?:
    | "kafka"
    | "kinesis"
    | "sqs"
    | "rabbitmq"
    | "google-pubsub"
    | "azure-event-hubs"
    | "azure-service-bus"
    | "pulsar";
}
export interface TopologyEdge {
  id: string;
  source: string;
  target: string;
  label?: string;
  confidence?: string;
}
