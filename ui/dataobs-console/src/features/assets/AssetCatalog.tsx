import { FormEvent, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, Asset } from "../../api/client";
import { useProductContext } from "../../state/context";

export function AssetCatalog() {
  const { tenant, environment } = useProductContext();
  const [params, setParams] = useSearchParams();
  const [assets, setAssets] = useState<Asset[]>([]);
  const [search, setSearch] = useState(params.get("search") ?? "");
  const [assetType, setAssetType] = useState(params.get("type") ?? "");
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [cursor, setCursor] = useState("");
  const [history, setHistory] = useState<string[]>([]);
  const [status, setStatus] = useState("Loading assets…");
  const load = (value = search) =>
    api
      .assets(tenant, environment, value, undefined, cursor, assetType)
      .then((result) => {
        setAssets(result.items);
        setNextCursor(result.next_cursor);
        setStatus(result.items.length ? "" : result.warnings[0]);
      })
      .catch(() => setStatus("Asset catalog is unavailable"));
  useEffect(() => {
    const controller = new AbortController();
    void api
      .assets(tenant, environment, search, controller.signal, cursor, assetType)
      .then((result) => {
        setAssets(result.items);
        setNextCursor(result.next_cursor);
        setStatus(result.items.length ? "" : result.warnings[0]);
      })
      .catch(() => setStatus("Asset catalog is unavailable"));
    return () => controller.abort();
  }, [tenant, environment, cursor, search, assetType]);
  const submit = (event: FormEvent) => {
    event.preventDefault();
    setCursor("");
    setHistory([]);
    setParams({
      ...(search ? { search } : {}),
      ...(assetType ? { type: assetType } : {}),
    });
    void load();
  };
  return (
    <section
      className="page investigation-page"
      aria-labelledby="asset-catalog-title"
    >
      <div className="eyebrow">
        CATALOG <span>/</span> ASSETS
      </div>
      <div className="page-title">
        <div>
          <h1 id="asset-catalog-title">Asset Catalog</h1>
          <p>
            Server-paginated operational inventory. Missing telemetry is never
            converted to zero.
          </p>
        </div>
        <Link className="button-link" to="/pathways">
          Open Pathway Explorer
        </Link>
      </div>
      <form className="investigation-toolbar" onSubmit={submit}>
        <label>
          Search by ID, FQN, name, tag or owner
          <input
            aria-label="Search assets"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="warehouse.public.orders"
          />
        </label>
        <label>
          Asset type
          <select
            value={assetType}
            onChange={(event) => setAssetType(event.target.value)}
          >
            <option value="">All types</option>
            <option value="table">Table</option>
            <option value="view">View</option>
            <option value="dataset">Dataset</option>
            <option value="service">Service</option>
          </select>
        </label>
        <button className="primary">Search</button>
      </form>
      {status && (
        <p role="status" className="notice">
          {status}
        </p>
      )}
      <div className="table-wrap">
        <table>
          <caption className="sr-only">
            Matching assets and their operational state
          </caption>
          <thead>
            <tr>
              <th>Name / FQN</th>
              <th>Type</th>
              <th>Health</th>
              <th>Owner</th>
              <th>Business service</th>
              <th>Source</th>
              <th>Environment</th>
            </tr>
          </thead>
          <tbody>
            {assets.map((asset) => (
              <tr key={asset.id}>
                <td>
                  <Link to={`/assets/${encodeURIComponent(asset.id)}`}>
                    {asset.fqn ?? asset.name}
                  </Link>
                </td>
                <td>{asset.asset_type ?? "unknown"}</td>
                <td>
                  <span className={`state ${asset.health ?? "unknown"}`}>
                    {asset.health ?? "unknown"}
                  </span>
                </td>
                <td>{asset.owner_team ?? "unknown"}</td>
                <td>{asset.business_service ?? "not configured"}</td>
                <td>{asset.source ?? "unknown"}</td>
                <td>{asset.environment ?? environment}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <nav className="pagination" aria-label="Asset catalog pages">
        <button
          disabled={!history.length}
          onClick={() => {
            const copy = [...history];
            setCursor(copy.pop() ?? "");
            setHistory(copy);
          }}
        >
          Previous
        </button>
        <button
          disabled={!nextCursor}
          onClick={() => {
            setHistory((values) => [...values, cursor]);
            setCursor(nextCursor ?? "");
          }}
        >
          Next
        </button>
      </nav>
    </section>
  );
}
