import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { incidentsApi, type IncidentItem } from "../../api/incidents";
import { useProductContext } from "../../state/context";

export function IncidentInbox() {
  const { tenant, environment } = useProductContext();
  const [params, setParams] = useSearchParams();
  const [items, setItems] = useState<IncidentItem[]>([]);
  const [next, setNext] = useState<string | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const load = (cursor?: string) => {
    setState("loading");
    const query = new URLSearchParams(params);
    query.delete("tenant");
    query.delete("environment");
    if (cursor) query.set("cursor", cursor);
    else query.delete("cursor");
    incidentsApi
      .list(tenant, environment, query)
      .then((data) => {
        setItems(data.items);
        setNext(data.next_cursor);
        setState("ready");
      })
      .catch(() => setState("error"));
  };
  const queryKey = params.toString();
  useEffect(() => {
    const query = new URLSearchParams(queryKey);
    query.delete("tenant");
    query.delete("environment");
    query.delete("cursor");
    incidentsApi
      .list(tenant, environment, query)
      .then((data) => {
        setItems(data.items);
        setNext(data.next_cursor);
        setState("ready");
      })
      .catch(() => setState("error"));
  }, [tenant, environment, queryKey]);
  const update = (key: string, value: string) => {
    const query = new URLSearchParams(params);
    if (value) query.set(key, value);
    else query.delete(key);
    query.delete("cursor");
    setParams(query);
  };
  return (
    <main className="page incident-page" aria-labelledby="incident-inbox-title">
      <div className="eyebrow">INCIDENT RESPONSE</div>
      <h1 id="incident-inbox-title">Incident Inbox</h1>
      <section className="panel" aria-label="Incident filters">
        <label>
          Search{" "}
          <input
            value={params.get("search") ?? ""}
            onChange={(e) => update("search", e.target.value)}
          />
        </label>
        <label>
          State{" "}
          <select
            value={params.get("state") ?? ""}
            onChange={(e) => update("state", e.target.value)}
          >
            <option value="">All states</option>
            <option>open</option>
            <option>acknowledged</option>
            <option>investigating</option>
            <option>resolved</option>
          </select>
        </label>
        <label>
          Severity{" "}
          <select
            value={params.get("severity") ?? ""}
            onChange={(e) => update("severity", e.target.value)}
          >
            <option value="">All severities</option>
            <option>critical</option>
            <option>high</option>
            <option>medium</option>
            <option>low</option>
          </select>
        </label>
        <label>
          Owner{" "}
          <input
            value={params.get("owner") ?? ""}
            onChange={(e) => update("owner", e.target.value)}
          />
        </label>
        <label>
          <input
            type="checkbox"
            checked={params.get("unassigned") === "true"}
            onChange={(e) =>
              update("unassigned", e.target.checked ? "true" : "")
            }
          />{" "}
          Unassigned
        </label>
        <label>
          Sort{" "}
          <select
            value={params.get("sort") ?? "recently_observed"}
            onChange={(e) => update("sort", e.target.value)}
          >
            <option value="recently_observed">Recently observed</option>
            <option value="newest_opened">Newest opened</option>
            <option value="severity">Severity</option>
            <option value="occurrence_count">Occurrences</option>
          </select>
        </label>
        <button onClick={() => setParams({ environment, tenant })}>
          Clear filters
        </button>
        <button onClick={() => load()}>Refresh</button>
      </section>
      <p role="status" aria-live="polite">
        {state === "loading"
          ? "Loading incidents…"
          : state === "error"
            ? "Incident data is unavailable."
            : `${items.length} incidents shown.`}
      </p>
      {state === "ready" && items.length === 0 ? (
        <section className="panel">
          <h2>No incidents match</h2>
          <p>Clear filters or refresh to check for active incidents.</p>
        </section>
      ) : null}
      {items.length ? (
        <div className="panel">
          <table>
            <caption>Environment-scoped incident inventory</caption>
            <thead>
              <tr>
                <th>Severity</th>
                <th>Incident</th>
                <th>State</th>
                <th>Owner</th>
                <th>Service</th>
                <th>Assets</th>
                <th>Occurrences</th>
                <th>Last observed</th>
                <th>Evidence</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id}>
                  <td>{item.severity}</td>
                  <th scope="row">
                    <Link to={`/incidents/${encodeURIComponent(item.id)}`}>
                      {item.title}
                    </Link>
                  </th>
                  <td>{item.state}</td>
                  <td>{item.owner || "Unassigned"}</td>
                  <td>{item.business_service || "Unknown"}</td>
                  <td>{item.affected_assets.join(", ") || "Unknown"}</td>
                  <td>{item.occurrence_count}</td>
                  <td>
                    {item.last_observed_at
                      ? new Date(item.last_observed_at).toLocaleString()
                      : "Unknown"}
                  </td>
                  <td>{item.data_status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
      {next ? <button onClick={() => load(next)}>Next page</button> : null}
    </main>
  );
}
