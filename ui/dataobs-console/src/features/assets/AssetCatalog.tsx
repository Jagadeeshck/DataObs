import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, Asset } from "../../api/client";
import { useProductContext } from "../../state/context";

export function AssetCatalog() {
  const { tenant, environment } = useProductContext();
  const [assets, setAssets] = useState<Asset[]>([]);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("Loading assets…");
  const load = (value = search) =>
    api
      .assets(tenant, environment, value)
      .then((result) => {
        setAssets(result.items);
        setStatus(result.items.length ? "" : result.warnings[0]);
      })
      .catch(() => setStatus("Asset catalog is unavailable"));
  useEffect(() => {
    const controller = new AbortController();
    void api
      .assets(tenant, environment, "", controller.signal)
      .then((result) => {
        setAssets(result.items);
        setStatus(result.items.length ? "" : result.warnings[0]);
      })
      .catch(() => setStatus("Asset catalog is unavailable"));
    return () => controller.abort();
  }, [tenant, environment]);
  const submit = (event: FormEvent) => {
    event.preventDefault();
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
    </section>
  );
}
