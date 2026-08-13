export function presentFacets(
  facets: Record<string, unknown> | null | undefined,
) {
  return Object.entries(facets ?? {}).filter(
    ([, value]) => value !== null && value !== undefined,
  );
}
