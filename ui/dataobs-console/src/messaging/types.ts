export type MessagingSystem =
  | "kafka"
  | "kinesis"
  | "sqs"
  | "rabbitmq"
  | "google_pubsub"
  | "azure_event_hubs"
  | "azure_service_bus"
  | "pulsar";

export type MessagingResourceKind =
  | "stream"
  | "topic"
  | "queue"
  | "exchange"
  | "subscription"
  | "consumer_group"
  | "shard"
  | "partition"
  | "namespace"
  | "broker"
  | "connector"
  | "dead_letter_queue"
  | "dead_letter_topic";

export type CapabilityState =
  | "supported"
  | "partial"
  | "not_configured"
  | "unavailable"
  | "unsupported";

export interface MessagingProviderEvidence {
  provider: string;
  messaging_system: MessagingSystem;
  configured: boolean;
  contract_capability: string;
  collection_capability: string;
  runtime_state: string;
  data_freshness: string;
  capabilities: Record<string, unknown>;
  limitations: string[];
  latest_observation?: string | null;
  source_coverage: number;
}

export interface MessagingProvidersResponse {
  items: MessagingProviderEvidence[];
  data_status?: string;
  warnings?: string[];
}

export type MetricEvidenceState =
  | "measured"
  | "estimated"
  | "inferred"
  | "forecast"
  | "missing"
  | "stale"
  | "partial"
  | "unavailable"
  | "unsupported";
