import type { ActivityItem, AttentionCategory } from "./types";
export const ATTENTION_POLICY_VERSION = "1.0";
export const attentionRules = [
  {
    capabilityId: "incidents",
    field: "severity",
    values: ["critical"],
    category: "critical",
  },
  {
    capabilityId: "incidents",
    field: "severity",
    values: ["high"],
    category: "warning",
  },
] as const;
export function classifyAttention(
  item: ActivityItem,
): AttentionCategory | undefined {
  for (const rule of attentionRules) {
    if (rule.capabilityId !== item.capabilityId) continue;
    const value = item[rule.field as "severity"];
    if (value && (rule.values as readonly string[]).includes(value))
      return rule.category;
  }
  return undefined;
}
