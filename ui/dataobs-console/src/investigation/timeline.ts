import {
  INVESTIGATION_LIMITS,
  type InvestigationEvidence,
  type RelatedEntity,
} from "./types";
const time = (item: InvestigationEvidence) =>
  Date.parse(item.effectiveAt ?? item.observedAt ?? "") || 0;
export function normaliseTimeline(items: InvestigationEvidence[]) {
  const unique = new Map<string, InvestigationEvidence>();
  for (const item of items)
    if (!unique.has(item.key)) unique.set(item.key, item);
  return [...unique.values()]
    .sort(
      (a, b) =>
        time(b) - time(a) ||
        a.capabilityId.localeCompare(b.capabilityId) ||
        a.key.localeCompare(b.key),
    )
    .slice(0, INVESTIGATION_LIMITS.timeline);
}
export function normaliseRelated(items: RelatedEntity[]) {
  return [...new Map(items.map((item) => [item.key, item])).values()].slice(
    0,
    INVESTIGATION_LIMITS.graphNodes - 1,
  );
}
