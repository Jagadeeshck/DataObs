import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, type DataProduct, ApiError } from "../../api/client";
import { useProductContext } from "../../state/context";

export function DataProductList() {
  const { tenant, environment } = useProductContext();
  const [params, setParams] = useSearchParams();
  const [items, setItems] = useState<DataProduct[]>([]);
  const [error, setError] = useState<string>();
  const [loading, setLoading] = useState(true);
  const refresh = params.get("refresh") ?? "0";
  useEffect(() => {
    const controller = new AbortController();
    api
      .dataProducts(tenant, environment, params, controller.signal)
      .then((result) => setItems(result.items))
      .catch((reason: unknown) =>
        setError(
          reason instanceof ApiError
            ? reason.message
            : "Data Products are unavailable",
        ),
      )
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [tenant, environment, params, refresh]);
  const update = (name: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(name, value);
    else next.delete(name);
    setLoading(true);
    setError(undefined);
    setParams(next);
  };
  return (
    <section aria-labelledby="data-products-title">
      <header>
        <h1 id="data-products-title">Data Products</h1>
        <p>Owned, measurable data capabilities and their current evidence.</p>
      </header>
      <form
        className="stream-filters"
        onSubmit={(event) => event.preventDefault()}
        aria-label="Data Product filters"
      >
        <label>
          Search
          <input
            value={params.get("search") ?? ""}
            onChange={(e) => update("search", e.target.value)}
          />
        </label>
        <label>
          Lifecycle
          <select
            value={params.get("lifecycle") ?? ""}
            onChange={(e) => update("lifecycle", e.target.value)}
          >
            <option value="">All</option>
            <option>draft</option>
            <option>active</option>
            <option>deprecated</option>
            <option>archived</option>
          </select>
        </label>
        <label>
          Criticality
          <select
            value={params.get("criticality") ?? ""}
            onChange={(e) => update("criticality", e.target.value)}
          >
            <option value="">All</option>
            <option>low</option>
            <option>medium</option>
            <option>high</option>
            <option>critical</option>
          </select>
        </label>
        <button
          type="button"
          onClick={() => update("refresh", String(Number(refresh) + 1))}
        >
          Refresh
        </button>
      </form>
      {loading && <p role="status">Loading Data Products…</p>}
      {error && (
        <div role="alert">
          <p>{error}</p>
          <button
            onClick={() => update("refresh", String(Number(refresh) + 1))}
          >
            Retry
          </button>
        </div>
      )}
      {!loading && !error && items.length === 0 && (
        <p>No Data Products match these filters.</p>
      )}
      {items.length > 0 && (
        <div className="table-scroll">
          <table>
            <caption>Data Product evidence</caption>
            <thead>
              <tr>
                <th>Name</th>
                <th>Domain</th>
                <th>Criticality</th>
                <th>Owner</th>
                <th>Lifecycle</th>
                <th>Reliability</th>
                <th>Coverage</th>
                <th>Open incidents</th>
                <th>Last evaluated</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id}>
                  <th scope="row">
                    <Link to={`/data-products/${encodeURIComponent(item.id)}`}>
                      {item.name}
                    </Link>
                  </th>
                  <td>{item.domain}</td>
                  <td>{item.criticality}</td>
                  <td>{item.owner.team}</td>
                  <td>{item.lifecycle_state}</td>
                  <td>Unknown</td>
                  <td>Unknown</td>
                  <td>Unknown</td>
                  <td>{new Date(item.updated_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
