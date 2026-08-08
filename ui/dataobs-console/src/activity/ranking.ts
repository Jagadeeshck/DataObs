import type { ActivityItem } from "./types";
const severity = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
  unknown: 4,
} as const;
const capability = [
  "incidents",
  "quality",
  "jobs",
  "streams",
  "pathways",
  "lineage",
  "integrations",
  "remediation",
  "workflows",
  "cases",
  "platform",
];
export function compareActivity(a: ActivityItem, b: ActivityItem) {
  return (
    Date.parse(b.occurredAt) - Date.parse(a.occurredAt) ||
    severity[a.severity ?? "unknown"] - severity[b.severity ?? "unknown"] ||
    capability.indexOf(a.capabilityId) - capability.indexOf(b.capabilityId) ||
    a.key.localeCompare(b.key)
  );
}
export function mergeActivity(items: ActivityItem[], maximum = 150) {
  const identities = new Set<string>();
  return items
    .sort(compareActivity)
    .filter((item) => {
      if (!item.canonicalEventId) return true;
      if (identities.has(item.canonicalEventId)) return false;
      identities.add(item.canonicalEventId);
      return true;
    })
    .slice(0, maximum);
}
