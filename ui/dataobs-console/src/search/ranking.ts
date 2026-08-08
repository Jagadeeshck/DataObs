import type { MatchCategory, SearchResult } from "./types";
const weights: Record<MatchCategory, number> = {
  exact_identifier: 0,
  exact_label: 1,
  prefix_label: 2,
  token_match: 3,
  provider_ranked: 4,
};
export function classifyMatch(
  query: string,
  id: string,
  label: string,
): MatchCategory {
  const q = query.trim().toLocaleLowerCase();
  if (id.toLocaleLowerCase() === q) return "exact_identifier";
  const normalized = label.toLocaleLowerCase();
  if (normalized === q) return "exact_label";
  if (normalized.startsWith(q)) return "prefix_label";
  if (normalized.split(/\s+/).some((token) => token.startsWith(q)))
    return "token_match";
  return "provider_ranked";
}
export const rankResults = (results: readonly SearchResult[]) =>
  [...results].sort(
    (a, b) =>
      weights[a.match] - weights[b.match] ||
      a.providerId.localeCompare(b.providerId) ||
      a.key.localeCompare(b.key),
  );
export function deduplicate(results: readonly SearchResult[]) {
  const seen = new Set<string>();
  return results.filter((item) => {
    const key = `${item.entityType}:${item.identifier}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}
