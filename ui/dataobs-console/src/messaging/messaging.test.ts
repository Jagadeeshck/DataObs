import { describe, expect, it } from "vitest";
import {
  capabilityState,
  formatMetric,
  messagingProviders,
  metricLabel,
  resourceLabel,
  safeMessagingTelemetry,
} from ".";
import type { MessagingProviderEvidence, MessagingSystem } from "./types";

const systems = Object.keys(messagingProviders) as MessagingSystem[];
const evidence = (
  overrides: Partial<MessagingProviderEvidence> = {},
): MessagingProviderEvidence => ({
  provider: "test",
  messaging_system: "sqs",
  configured: true,
  contract_capability: "supported",
  collection_capability: "collecting",
  runtime_state: "available",
  data_freshness: "fresh",
  capabilities: { inventory: true, lag: false, delivery: "partial" },
  limitations: [],
  source_coverage: 1,
  ...overrides,
});

describe("messaging presentation", () => {
  it("defines distinct terminology for all eight authoritative systems", () => {
    expect(systems).toHaveLength(8);
    expect(resourceLabel("kafka", "topic")).toBe("Topic");
    expect(resourceLabel("kinesis", "shard")).toBe("Shard");
    expect(resourceLabel("sqs", "queue")).toBe("Queue");
    expect(resourceLabel("rabbitmq", "exchange")).toBe("Exchange");
    expect(resourceLabel("google_pubsub", "subscription")).toBe("Subscription");
    expect(resourceLabel("azure_event_hubs", "stream")).toBe("Event hub");
    expect(resourceLabel("azure_service_bus", "dead_letter_queue")).toBe(
      "Dead-letter queue",
    );
    expect(resourceLabel("pulsar", "namespace")).toBe("Namespace");
    expect(metricLabel("sqs", "backlog")).toBe("Visible messages");
    expect(metricLabel("kafka", "backlog")).toBe("Maximum consumer lag");
  });

  it("preserves negotiated capability states", () => {
    expect(capabilityState(evidence(), "inventory")).toBe("supported");
    expect(capabilityState(evidence(), "lag")).toBe("unsupported");
    expect(capabilityState(evidence(), "delivery")).toBe("partial");
    expect(capabilityState(evidence({ configured: false }), "inventory")).toBe(
      "not_configured",
    );
    expect(
      capabilityState(evidence({ runtime_state: "unavailable" }), "inventory"),
    ).toBe("unavailable");
  });

  it("distinguishes measured zero, missing, unavailable, and unsupported", () => {
    expect(formatMetric(0, "measured", "messages")).toBe("0 messages");
    expect(formatMetric(undefined, "missing")).toBe("No observation");
    expect(formatMetric(undefined, "unavailable")).toBe("Unavailable");
    expect(formatMetric(0, "unsupported")).toBe("Not applicable");
  });

  it("drops identifying telemetry fields", () => {
    expect(
      safeMessagingTelemetry({
        provider_type: "sqs",
        resource_id: "secret",
        tenant_id: "tenant",
      }),
    ).toEqual({ provider_type: "sqs" });
  });
});
