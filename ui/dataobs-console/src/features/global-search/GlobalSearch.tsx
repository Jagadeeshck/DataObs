import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { buildRoutePath } from "../../app/routes";
import {
  SearchController,
  searchProviders,
  type SearchSnapshot,
} from "../../search";
import { useProductContext } from "../../state/context";

export function GlobalSearch() {
  const { tenant, environment, identity } = useProductContext();
  const controller = useMemo(() => new SearchController(searchProviders), []);
  const [query, setQuery] = useState("");
  const [snapshot, setSnapshot] = useState<SearchSnapshot>();
  const [provider, setProvider] = useState("all");
  const navigate = useNavigate();
  const input = useRef<HTMLInputElement>(null);
  useEffect(() => {
    if (query.trim().length < 2) {
      controller.cancel();
      // eslint-disable-next-line react-hooks/set-state-in-effect -- clearing a sensitive in-memory query invalidates prior results
      setSnapshot(undefined);
      return;
    }
    const timer = setTimeout(
      () =>
        void controller.search(
          query,
          {
            tenant,
            environment,
            permissions: identity?.permissions ?? [],
            capabilities: identity?.capabilities,
          },
          setSnapshot,
        ),
      250,
    );
    return () => {
      clearTimeout(timer);
      controller.cancel();
    };
  }, [
    controller,
    environment,
    identity?.capabilities,
    identity?.permissions,
    query,
    tenant,
  ]);
  const results = (snapshot?.results ?? []).filter(
    (r) => provider === "all" || r.providerId === provider,
  );
  return (
    <main className="page global-search">
      <header className="page-header">
        <div>
          <p className="eyebrow">Discovery</p>
          <h1>Global Search</h1>
          <p>
            Bounded search in the current tenant and environment. Queries stay
            in memory and are never included in telemetry.
          </p>
        </div>
      </header>
      <div className="search-controls">
        <label htmlFor="global-search-input">Search operational entities</label>
        <input
          ref={input}
          id="global-search-input"
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          autoComplete="off"
          maxLength={256}
          placeholder="Enter at least 2 characters"
        />{" "}
        <button
          onClick={() => {
            setQuery("");
            input.current?.focus();
          }}
        >
          Clear
        </button>
      </div>
      <label>
        Provider{" "}
        <select value={provider} onChange={(e) => setProvider(e.target.value)}>
          <option value="all">All providers</option>
          {searchProviders.map((p) => (
            <option key={p.id} value={p.id}>
              {p.label}
            </option>
          ))}
        </select>
      </label>
      <p role="status" aria-live="polite">
        {snapshot?.searching
          ? `Searching; ${results.length} results available`
          : query.length < 2
            ? "Enter at least two characters"
            : `${results.length} results`}
      </p>
      <ul className="search-results" aria-label="Entity search results">
        {results.map((item) => {
          const path = buildRoutePath(item.routeId, item.routeParameters);
          return (
            path && (
              <li key={item.key}>
                <button onClick={() => navigate(path)}>
                  <strong>{item.label}</strong>
                  <span>
                    {item.entityType.replaceAll("_", " ")} ·{" "}
                    {item.health ?? "Evidence state unavailable"}
                  </span>
                </button>
              </li>
            )
          );
        })}
      </ul>
      {!snapshot?.searching && query.length >= 2 && !results.length && (
        <p>No matching entities were returned by available providers.</p>
      )}
      {snapshot && (
        <details>
          <summary>Provider status</summary>
          <ul>
            {snapshot.providers.map((p) => (
              <li key={p.providerId}>
                {p.label}: {p.status.replaceAll("_", " ")} ({p.resultCount}{" "}
                results, {p.durationBucket})
              </li>
            ))}
          </ul>
        </details>
      )}
      <p>
        <Link to="/">Return to Command Center</Link>
      </p>
    </main>
  );
}
