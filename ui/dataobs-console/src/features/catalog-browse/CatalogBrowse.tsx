import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { buildRoutePath } from "../../app/routes";
import { useProductContext } from "../../state/context";
import {
  fetchCatalogPage,
  type CatalogError,
  type CatalogPage,
} from "../../api/catalogSearch";
import {
  aggregateFacets,
  applyFacetSelections,
  rankAssets,
  toggleSelection,
  type FacetSelection,
} from "../../search/catalog";
import {
  FacetPanel,
  SearchField,
  SelectedFacets,
} from "../../components/Facets";
import {
  DataStatusBanner,
  EmptyState,
  ErrorState,
  LoadingSkeleton,
} from "../../components/Evidence";

type FetchState =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "ready"; page: CatalogPage }
  | { kind: "error"; error: CatalogError };

/**
 * Catalog browse groundwork surface (Team 5).
 *
 * Wires the shared search bar + facet panel to the asset-search contract and keeps
 * loading, error, measured-zero and ready as strictly separate states. Relevance
 * ranking and facet aggregation run client-side over the bounded result page today;
 * when the Team 2 asset-search endpoint and the Team 0 `0035` mapping land, only the
 * client transport changes. Degrades to an honest empty/unavailable state ahead of
 * the endpoint rather than implying a measured zero.
 */
export function CatalogBrowse() {
  const { tenant, environment, refreshGeneration } = useProductContext();
  const [query, setQuery] = useState("");
  const [selections, setSelections] = useState<readonly FacetSelection[]>([]);
  const [state, setState] = useState<FetchState>({ kind: "idle" });
  const [reloadToken, setReloadToken] = useState(0);
  const navigate = useNavigate();

  useEffect(() => {
    if (!tenant || !environment) return;
    const controller = new AbortController();
    const search = query.trim();
    // eslint-disable-next-line react-hooks/set-state-in-effect -- a new query/context invalidates prior results immediately
    setState({ kind: "loading" });
    const timer = setTimeout(() => {
      void fetchCatalogPage(
        { tenant, environment, search },
        controller.signal,
      ).then((result) => {
        if (controller.signal.aborted) return;
        setState(
          "page" in result
            ? { kind: "ready", page: result.page }
            : { kind: "error", error: result.error },
        );
      });
    }, 250);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [tenant, environment, query, refreshGeneration, reloadToken]);

  const assets = useMemo(
    () => (state.kind === "ready" ? state.page.items : []),
    [state],
  );
  const filtered = useMemo(
    () => applyFacetSelections(assets, selections),
    [assets, selections],
  );
  const facets = useMemo(() => aggregateFacets(assets), [assets]);
  const ranked = useMemo(() => rankAssets(filtered, query), [filtered, query]);

  const resultSummary =
    state.kind === "loading"
      ? "Loading catalog results…"
      : state.kind === "ready"
        ? `${ranked.length} ${ranked.length === 1 ? "asset" : "assets"}`
        : "";

  return (
    <main className="page catalog-browse">
      <header className="page-header">
        <div>
          <p className="eyebrow">Discovery</p>
          <h1>Catalog Browse</h1>
          <p>
            Browse and refine data assets in the current tenant and environment.
            Queries stay in memory and are never included in telemetry. Semantic
            relevance and server-side facets become available once the catalog
            search backend is configured.
          </p>
        </div>
      </header>

      <div className="catalog-layout">
        <aside className="catalog-sidebar">
          <SearchField
            label="Search assets"
            value={query}
            onChange={setQuery}
            onClear={() => setQuery("")}
          />
          <FacetPanel
            facets={facets}
            selections={selections}
            onToggle={(selection) =>
              setSelections((current) => toggleSelection(current, selection))
            }
          />
        </aside>

        <section className="catalog-results" aria-label="Catalog results">
          <SelectedFacets
            selections={selections}
            onToggle={(selection) =>
              setSelections((current) => toggleSelection(current, selection))
            }
            onClear={() => setSelections([])}
          />
          <p role="status" aria-live="polite">
            {resultSummary}
          </p>

          {state.kind === "loading" && (
            <LoadingSkeleton label="Loading catalog assets…" />
          )}

          {state.kind === "error" && (
            <ErrorState
              message={state.error.message}
              requestId={state.error.requestId}
              retry={() => setReloadToken((value) => value + 1)}
            />
          )}

          {state.kind === "ready" && state.page.dataStatus !== "complete" && (
            <DataStatusBanner state={state.page.dataStatus}>
              {state.page.warnings[0] ??
                "Catalog evidence is incomplete for this context."}
            </DataStatusBanner>
          )}

          {state.kind === "ready" && ranked.length === 0 && (
            <EmptyState title="No matching assets">
              <p>
                {selections.length > 0 || query.trim().length > 0
                  ? "No assets match the current search and filters in this environment."
                  : "No assets have been observed in this tenant and environment yet."}
              </p>
            </EmptyState>
          )}

          {state.kind === "ready" && ranked.length > 0 && (
            <ul className="catalog-asset-list">
              {ranked.map(({ asset, matchedFields }) => {
                const path = buildRoutePath("asset-360", { assetId: asset.id });
                return (
                  <li key={asset.id}>
                    <button
                      type="button"
                      onClick={() => path && navigate(path)}
                      disabled={!path}
                    >
                      <strong>{asset.name || asset.id}</strong>
                      <span>
                        {(asset.asset_type ?? "asset").replaceAll("_", " ")} ·{" "}
                        {asset.health ?? "Evidence state unavailable"}
                      </span>
                      {matchedFields.length > 0 && (
                        <small>Matched on {matchedFields.join(", ")}</small>
                      )}
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </section>
      </div>

      <p>
        <Link to="/assets">Open the full asset catalog</Link> ·{" "}
        <Link to="/search">Global search</Link>
      </p>
    </main>
  );
}
