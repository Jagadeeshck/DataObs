import { providerPresentation } from "./providers";
import type { MessagingResourceKind, MessagingSystem } from "./types";

const metrics: Record<MessagingSystem, Record<string, string>> = {
  kafka: {
    backlog: "Maximum consumer lag",
    age: "Processing delay",
    throughput: "Records per second",
  },
  kinesis: {
    backlog: "Iterator age",
    age: "Iterator age",
    throughput: "Events per second",
  },
  sqs: {
    backlog: "Visible messages",
    age: "Oldest message age",
    throughput: "Messages per second",
  },
  rabbitmq: {
    backlog: "Ready messages",
    age: "Message age",
    throughput: "Messages per second",
  },
  google_pubsub: {
    backlog: "Unacked messages",
    age: "Oldest unacked message age",
    throughput: "Messages per second",
  },
  azure_event_hubs: {
    backlog: "Consumer lag",
    age: "Processing delay",
    throughput: "Events per second",
  },
  azure_service_bus: {
    backlog: "Active messages",
    age: "Oldest message age",
    throughput: "Messages per second",
  },
  pulsar: {
    backlog: "Subscription backlog",
    age: "Oldest backlog message age",
    throughput: "Messages per second",
  },
};

export function resourceLabel(
  system: MessagingSystem,
  kind: MessagingResourceKind,
): string {
  return (
    providerPresentation(system).resourceLabels[kind] ??
    kind.replaceAll("_", " ").replace(/^./, (x) => x.toUpperCase())
  );
}
export function metricLabel(
  system: MessagingSystem,
  metric: "backlog" | "age" | "throughput",
): string {
  return metrics[system][metric];
}
