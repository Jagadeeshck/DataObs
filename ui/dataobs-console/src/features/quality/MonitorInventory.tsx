import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { qualityApi, type MonitorDefinition } from "../../api/quality";
import { useProductContext } from "../../state/context";
import { shown } from "./Evidence";
export function MonitorInventory() {
  const { tenant, environment } = useProductContext();
  const [params, setParams] = useSearchParams();
  const [items, setItems] = useState<MonitorDefinition[]>([]);
  const [next, setNext] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    const c = new AbortController();
    qualityApi
      .monitors(tenant, environment, params, c.signal)
      .then((x) => {
        setItems(x.data.items);
        setNext(x.data.next_cursor);
        setError("");
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
    return () => c.abort();
  }, [tenant, environment, params]);
  const update = (key: string, value: string) => {
    const q = new URLSearchParams(params);
    if (value) q.set(key, value);
    else q.delete(key);
    q.delete("cursor");
    setParams(q);
  };
  return (
    <section className="quality-page">
      <nav aria-label="Breadcrumb">
        <Link to="/quality">Quality</Link> / Monitors
      </nav>
      <div className="quality-heading">
        <div>
          <h1>Monitor inventory</h1>
          <p>
            Bounded server-side results for the current tenant and environment.
          </p>
        </div>
        <Link className="primary-action" to="/quality/monitors/new">
          Create monitor
        </Link>
      </div>
      <form className="stream-filters" onSubmit={(e) => e.preventDefault()}>
        <label>
          Search
          <input
            value={params.get("search") ?? ""}
            onChange={(e) => update("search", e.target.value)}
          />
        </label>
        <label>
          State
          <select
            value={params.get("state") ?? ""}
            onChange={(e) => update("state", e.target.value)}
          >
            <option value="">All states</option>
            {[
              "draft",
              "enabled",
              "disabled",
              "learning",
              "active",
              "degraded",
              "error",
              "archived",
            ].map((x) => (
              <option key={x}>{x}</option>
            ))}
          </select>
        </label>
        <label>
          Type
          <input
            value={params.get("monitor_type") ?? ""}
            onChange={(e) => update("monitor_type", e.target.value)}
          />
        </label>
        <label>
          Source
          <select
            value={params.get("source_type") ?? ""}
            onChange={(e) => update("source_type", e.target.value)}
          >
            <option value="">All sources</option>
            <option value="postgresql">PostgreSQL</option>
            <option value="deterministic_test">Deterministic test</option>
          </select>
        </label>
        <button
          type="button"
          onClick={() => setParams({ limit: "50", sort: "name" })}
        >
          Reset filters
        </button>
      </form>
      {loading && <p role="status">Loading monitor inventory…</p>}
      {error && <p role="alert">Monitor inventory unavailable: {error}</p>}
      {!loading && !error && items.length === 0 && (
        <p>
          No monitors match these filters. Missing results are not counted as
          zero.
        </p>
      )}
      <div className="table-scroll">
        <table>
          <caption>Quality monitors</caption>
          <thead>
            <tr>
              <th>Monitor</th>
              <th>Type / target</th>
              <th>State</th>
              <th>Schedule</th>
              <th>Threshold</th>
              <th>Revision</th>
            </tr>
          </thead>
          <tbody>
            {items.map((m) => (
              <tr key={m.id}>
                <th>
                  <Link to={`/quality/monitors/${encodeURIComponent(m.id)}`}>
                    {m.name || m.id}
                  </Link>
                  <small>{m.id}</small>
                </th>
                <td>
                  {m.monitor_type}
                  <small>
                    {shown(
                      m.target.asset_id ??
                        `${m.target.schema_name ?? ""}.${m.target.table_name ?? ""}`,
                    )}
                  </small>
                </td>
                <td>
                  <span className={`state state-${m.state}`}>{m.state}</span>
                </td>
                <td>
                  {m.schedule.interval} · {m.schedule.timezone}
                </td>
                <td>{m.threshold.mode}</td>
                <td>{m.revision}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {next && (
        <button onClick={() => update("cursor", next)}>Next page</button>
      )}
    </section>
  );
}
