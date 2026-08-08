import type { EntityType } from "../app/entityLinks";
const allowed = new Set([
  "investigation_opened",
  "provider_outcome",
  "filter_changed",
  "related_entity_selected",
  "handoff",
  "investigation_closed",
]);
export function safeInvestigationTelemetry(
  event: string,
  values: {
    anchorType?: EntityType;
    providerOutcome?: string;
    evidenceCount?: number;
    providerCount?: number;
    handoffCapability?: string;
  } = {},
) {
  if (!allowed.has(event)) return;
  return {
    event,
    ...(values.anchorType ? { anchor_type: values.anchorType } : {}),
    ...(values.providerOutcome
      ? { provider_outcome: values.providerOutcome }
      : {}),
    ...(values.evidenceCount !== undefined
      ? {
          evidence_count_bucket:
            values.evidenceCount === 0
              ? "0"
              : values.evidenceCount <= 10
                ? "1-10"
                : values.evidenceCount <= 50
                  ? "11-50"
                  : "51-100",
        }
      : {}),
    ...(values.providerCount !== undefined
      ? { provider_count: Math.min(values.providerCount, 10) }
      : {}),
    ...(values.handoffCapability
      ? { handoff_capability: values.handoffCapability.slice(0, 32) }
      : {}),
  };
}
