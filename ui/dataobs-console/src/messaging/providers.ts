import type { MessagingResourceKind, MessagingSystem } from "./types";

export interface MessagingProviderPresentation {
  system: MessagingSystem;
  displayName: string;
  shortName: string;
  mark: string;
  resourceLabels: Partial<Record<MessagingResourceKind, string>>;
}

// Presentation only. Support and configuration always come from /streams/providers.
export const messagingProviders: Record<
  MessagingSystem,
  MessagingProviderPresentation
> = {
  kafka: {
    system: "kafka",
    displayName: "Apache Kafka",
    shortName: "Kafka",
    mark: "K",
    resourceLabels: {
      topic: "Topic",
      partition: "Partition",
      consumer_group: "Consumer group",
      broker: "Broker",
      connector: "Connector",
    },
  },
  kinesis: {
    system: "kinesis",
    displayName: "Amazon Kinesis",
    shortName: "Kinesis",
    mark: "K",
    resourceLabels: {
      stream: "Stream",
      shard: "Shard",
      subscription: "Consumer",
    },
  },
  sqs: {
    system: "sqs",
    displayName: "Amazon SQS",
    shortName: "SQS",
    mark: "S",
    resourceLabels: { queue: "Queue", dead_letter_queue: "Dead-letter queue" },
  },
  rabbitmq: {
    system: "rabbitmq",
    displayName: "RabbitMQ",
    shortName: "RabbitMQ",
    mark: "R",
    resourceLabels: {
      queue: "Queue",
      exchange: "Exchange",
      subscription: "Consumer",
    },
  },
  google_pubsub: {
    system: "google_pubsub",
    displayName: "Google Pub/Sub",
    shortName: "Pub/Sub",
    mark: "P",
    resourceLabels: { topic: "Topic", subscription: "Subscription" },
  },
  azure_event_hubs: {
    system: "azure_event_hubs",
    displayName: "Azure Event Hubs",
    shortName: "Event Hubs",
    mark: "E",
    resourceLabels: {
      namespace: "Namespace",
      stream: "Event hub",
      partition: "Partition",
      consumer_group: "Consumer group",
    },
  },
  azure_service_bus: {
    system: "azure_service_bus",
    displayName: "Azure Service Bus",
    shortName: "Service Bus",
    mark: "S",
    resourceLabels: {
      namespace: "Namespace",
      queue: "Queue",
      topic: "Topic",
      subscription: "Subscription",
      dead_letter_queue: "Dead-letter queue",
    },
  },
  pulsar: {
    system: "pulsar",
    displayName: "Apache Pulsar",
    shortName: "Pulsar",
    mark: "P",
    resourceLabels: {
      namespace: "Namespace",
      topic: "Topic",
      partition: "Partition",
      subscription: "Subscription",
    },
  },
};

export const providerPresentation = (system: MessagingSystem) =>
  messagingProviders[system];
