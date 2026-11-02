/**
 * Catalog browse groundwork: client-side BM25 relevance scoring and facet
 * aggregation over asset-search results.
 *
 * This is deliberately a groundwork layer. When the Team 2 asset-search contract
 * (and the Team 0 `0035` semantic-search mapping it depends on) land, the backend
 * returns server-ranked results and server-computed facet counts. Until then the
 * Console degrades gracefully: it ranks and facets whatever bounded result page
 * the existing `/api/v1/assets` endpoint returns, and never fabricates matches.
 *
 * Honesty rules preserved:
 * - A facet with zero matches in the current page is a measured zero (count 0),
 *   which is distinct from a facet dimension that was never reported (absent).
 * - Relevance is explainable and deterministic; ties break on a stable key.
 */
import type { Asset } from "../api";

export type FacetDimension = "asset_type" | "owner_team" | "source" | "health";

export interface FacetValue {
  value: string;
  /** Measured count within the current result page. Zero is a real zero. */
  count: number;
}

export interface Facet {
  dimension: FacetDimension;
  label: string;
  /** Sorted descending by count, then value. Empty array = measured zero values. */
  values: FacetValue[];
}

export interface FacetSelection {
  dimension: FacetDimension;
  value: string;
}

export interface RankedAsset {
  asset: Asset;
  score: number;
  /** Which fields contributed, for explainable ranking. */
  matchedFields: string[];
}

const FACET_FIELDS: Array<{ dimension: FacetDimension; label: string }> = [
  { dimension: "asset_type", label: "Asset type" },
  { dimension: "owner_team", label: "Owner team" },
  { dimension: "source", label: "Source" },
  { dimension: "health", label: "Health" },
];

const facetFieldValue = (
  asset: Asset,
  dimension: FacetDimension,
): string | undefined => {
  switch (dimension) {
    case "asset_type":
      return asset.asset_type;
    case "owner_team":
      return asset.owner_team;
    case "source":
      return asset.source;
    case "health":
      return asset.health;
  }
};

/**
 * Tokenise for BM25. Lowercased, split on non-alphanumerics, empty tokens dropped.
 */
export const tokenise = (text: string): string[] =>
  text
    .toLocaleLowerCase()
    .split(/[^a-z0-9]+/i)
    .filter(Boolean);

const BM25_K1 = 1.2;
const BM25_B = 0.75;

interface SearchableField {
  key: string;
  text: string;
  /** Field weight — identifiers and names matter more than free text. */
  boost: number;
}

const searchableFields = (asset: Asset): SearchableField[] =>
  [
    { key: "name", text: asset.name ?? "", boost: 3 },
    { key: "id", text: asset.id ?? "", boost: 2.5 },
    { key: "fqn", text: asset.fqn ?? "", boost: 2 },
    { key: "asset_type", text: asset.asset_type ?? "", boost: 1 },
    { key: "business_service", text: asset.business_service ?? "", boost: 1 },
    { key: "owner_team", text: asset.owner_team ?? "", boost: 1 },
  ].filter((field) => field.text.length > 0);

/**
 * Rank a bounded page of assets against the query using a BM25 variant.
 *
 * With an empty query every asset scores 0 and the original (server) order is
 * preserved — this keeps "browse" distinct from "search" and avoids inventing
 * relevance where the user supplied no terms.
 */
export function rankAssets(
  assets: readonly Asset[],
  query: string,
): RankedAsset[] {
  const terms = tokenise(query);
  if (assets.length === 0) return [];
  if (terms.length === 0)
    return assets.map((asset) => ({ asset, score: 0, matchedFields: [] }));

  // Document frequency per term across the current page corpus.
  const docFrequency = new Map<string, number>();
  const perAssetTokens = assets.map((asset) => {
    const fields = searchableFields(asset);
    const tokensByField = fields.map((field) => ({
      ...field,
      tokens: tokenise(field.text),
    }));
    const seen = new Set<string>();
    for (const field of tokensByField)
      for (const token of field.tokens) seen.add(token);
    for (const token of seen)
      docFrequency.set(token, (docFrequency.get(token) ?? 0) + 1);
    return tokensByField;
  });

  const corpusSize = assets.length;
  const avgFieldLength =
    perAssetTokens.reduce(
      (sum, fields) =>
        sum + fields.reduce((inner, f) => inner + f.tokens.length, 0),
      0,
    ) / corpusSize || 1;

  const ranked = assets.map((asset, index) => {
    const fields = perAssetTokens[index];
    const fieldLength = fields.reduce((sum, f) => sum + f.tokens.length, 0) || 1;
    const matchedFields = new Set<string>();
    let score = 0;
    for (const term of terms) {
      const df = docFrequency.get(term) ?? 0;
      if (df === 0) continue;
      const idf = Math.log(1 + (corpusSize - df + 0.5) / (df + 0.5));
      for (const field of fields) {
        const termFrequency = field.tokens.filter((t) => t === term).length;
        if (termFrequency === 0) continue;
        matchedFields.add(field.key);
        const denominator =
          termFrequency +
          BM25_K1 * (1 - BM25_B + (BM25_B * fieldLength) / avgFieldLength);
        score +=
          field.boost *
          idf *
          ((termFrequency * (BM25_K1 + 1)) / denominator);
      }
    }
    return { asset, score, matchedFields: [...matchedFields] };
  });

  return ranked.sort(
    (a, b) =>
      b.score - a.score ||
      (a.asset.name ?? a.asset.id).localeCompare(b.asset.name ?? b.asset.id) ||
      a.asset.id.localeCompare(b.asset.id),
  );
}

/**
 * Aggregate facet counts over a result page. A dimension is only emitted when at
 * least one asset reports it, so a fully absent dimension stays absent rather than
 * being shown as a misleading measured zero.
 */
export function aggregateFacets(assets: readonly Asset[]): Facet[] {
  return FACET_FIELDS.map(({ dimension, label }) => {
    const counts = new Map<string, number>();
    let reported = false;
    for (const asset of assets) {
      const value = facetFieldValue(asset, dimension);
      if (value === undefined || value === "") continue;
      reported = true;
      counts.set(value, (counts.get(value) ?? 0) + 1);
    }
    if (!reported) return null;
    const values = [...counts.entries()]
      .map(([value, count]) => ({ value, count }))
      .sort((a, b) => b.count - a.count || a.value.localeCompare(b.value));
    return { dimension, label, values };
  }).filter((facet): facet is Facet => facet !== null);
}

/** Apply the current facet selection (AND across dimensions, OR within one). */
export function applyFacetSelections(
  assets: readonly Asset[],
  selections: readonly FacetSelection[],
): Asset[] {
  if (selections.length === 0) return [...assets];
  const byDimension = new Map<FacetDimension, Set<string>>();
  for (const selection of selections) {
    const set = byDimension.get(selection.dimension) ?? new Set<string>();
    set.add(selection.value);
    byDimension.set(selection.dimension, set);
  }
  return assets.filter((asset) =>
    [...byDimension.entries()].every(([dimension, values]) => {
      const current = facetFieldValue(asset, dimension);
      return current !== undefined && values.has(current);
    }),
  );
}

export const toggleSelection = (
  selections: readonly FacetSelection[],
  candidate: FacetSelection,
): FacetSelection[] => {
  const exists = selections.some(
    (s) => s.dimension === candidate.dimension && s.value === candidate.value,
  );
  return exists
    ? selections.filter(
        (s) =>
          !(s.dimension === candidate.dimension && s.value === candidate.value),
      )
    : [...selections, candidate];
};
