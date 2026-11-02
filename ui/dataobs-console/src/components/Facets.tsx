/**
 * Shared, accessible search and facet primitives for catalog-style browse surfaces.
 * Owned by Team 5 (Console shell / shared components). Presentation only — no data
 * fetching, no domain API semantics.
 */
import { useId } from "react";
import type { Facet, FacetSelection } from "../search/catalog";

export function SearchField({
  label,
  value,
  onChange,
  onClear,
  placeholder = "Search the catalog",
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  onClear: () => void;
  placeholder?: string;
}) {
  const id = useId();
  return (
    <div className="catalog-search-field">
      <label htmlFor={id}>{label}</label>
      <input
        id={id}
        type="search"
        role="searchbox"
        value={value}
        autoComplete="off"
        maxLength={256}
        placeholder={placeholder}
        onChange={(event) => onChange(event.target.value)}
      />
      <button type="button" onClick={onClear} disabled={value.length === 0}>
        Clear
      </button>
    </div>
  );
}

const isSelected = (
  selections: readonly FacetSelection[],
  dimension: FacetSelection["dimension"],
  value: string,
) => selections.some((s) => s.dimension === dimension && s.value === value);

export function FacetPanel({
  facets,
  selections,
  onToggle,
}: {
  facets: readonly Facet[];
  selections: readonly FacetSelection[];
  onToggle: (selection: FacetSelection) => void;
}) {
  if (facets.length === 0) return null;
  return (
    <nav className="catalog-facets" aria-label="Refine catalog results">
      {facets.map((facet) => (
        <fieldset key={facet.dimension} className="catalog-facet">
          <legend>{facet.label}</legend>
          {facet.values.length === 0 ? (
            <p className="catalog-facet-empty">
              No values reported in these results.
            </p>
          ) : (
            <ul>
              {facet.values.map((entry) => {
                const checked = isSelected(
                  selections,
                  facet.dimension,
                  entry.value,
                );
                return (
                  <li key={entry.value}>
                    <label>
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() =>
                          onToggle({
                            dimension: facet.dimension,
                            value: entry.value,
                          })
                        }
                      />
                      <span>{entry.value}</span>
                      <span
                        className="catalog-facet-count"
                        aria-label={`${entry.count} matching`}
                      >
                        {entry.count}
                      </span>
                    </label>
                  </li>
                );
              })}
            </ul>
          )}
        </fieldset>
      ))}
    </nav>
  );
}

export function SelectedFacets({
  selections,
  onToggle,
  onClear,
}: {
  selections: readonly FacetSelection[];
  onToggle: (selection: FacetSelection) => void;
  onClear: () => void;
}) {
  if (selections.length === 0) return null;
  return (
    <div className="catalog-selected-facets" aria-label="Active filters">
      {selections.map((selection) => (
        <button
          key={`${selection.dimension}:${selection.value}`}
          type="button"
          className="catalog-facet-chip"
          onClick={() => onToggle(selection)}
          aria-label={`Remove filter ${selection.dimension} ${selection.value}`}
        >
          {selection.value} ✕
        </button>
      ))}
      <button type="button" onClick={onClear}>
        Clear all filters
      </button>
    </div>
  );
}
