import type {
  EvidenceAvailability,
  EvidenceKind,
  HealthState,
  MetricUnit,
} from "./types";
export const evidenceLabels: Record<EvidenceKind, string> = {
  measured: "Measured",
  estimated: "Estimated",
  inferred: "Inferred",
  forecast: "Forecast",
};
export const availabilityLabels: Record<EvidenceAvailability, string> = {
  available: "Available",
  partial: "Partial coverage",
  stale: "Stale",
  missing: "No observation",
  unknown: "Unknown",
  unavailable: "Unavailable",
};
export const healthLabels: Record<HealthState, string> = {
  healthy: "Healthy",
  warning: "Warning",
  critical: "Critical",
  unknown: "Unknown",
};
export const validUnits: readonly MetricUnit[] = [
  "count",
  "percent",
  "bytes",
  "ms",
  "seconds",
  "msg/s",
  "events/s",
  "rows/s",
  "records",
  "score",
];
export function meaningfulPercentDifference(
  current: number | null,
  previous: number | null,
  compatibleCoverage = true,
): number | null {
  if (
    current == null ||
    previous == null ||
    previous === 0 ||
    !compatibleCoverage
  )
    return null;
  return ((current - previous) / Math.abs(previous)) * 100;
}
export const messagingMetricLabels = {
  backlog: "Backlog",
  consumerLag: "Consumer lag",
  messageAge: "Message age",
  queueDepth: "Queue depth",
  deliveryDelay: "Delivery delay",
} as const;
