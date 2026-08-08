import type { SearchContext, SearchProvider } from "./types";
export function createRegistry(providers: readonly SearchProvider[]) {
  const sorted = [...providers].sort((a, b) => a.id.localeCompare(b.id));
  if (new Set(sorted.map((p) => p.id)).size !== sorted.length)
    throw new Error("Duplicate search provider ID");
  for (const provider of sorted)
    if (
      provider.maximumResults < 1 ||
      provider.maximumResults > 25 ||
      provider.timeoutMs < 100 ||
      provider.timeoutMs > 2_000 ||
      provider.minimumQueryLength < 2
    )
      throw new Error(`Unsafe search provider contract: ${provider.id}`);
  return sorted;
}
export const canSearch = (provider: SearchProvider, context: SearchContext) =>
  (!provider.requiredPermission ||
    context.permissions.includes(provider.requiredPermission)) &&
  context.capabilities?.[provider.capabilityId] !== "not_configured" &&
  context.capabilities?.[provider.capabilityId] !== "unavailable" &&
  provider.isAvailable(context);
