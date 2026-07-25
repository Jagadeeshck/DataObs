import { useEffect, useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, type StreamList } from "../../api/client";
import { useProductContext } from "../../state/context";

export function StreamsInventory() {
  const { tenant, environment } = useProductContext();
  const [params, setParams] = useSearchParams();
  const [result, setResult] = useState<StreamList>();
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    const query = new URLSearchParams(params);
    query.set("limit", "50");
    api
      .streams(tenant, environment, query, controller.signal)
      .then(setResult)
      .catch((cause: unknown) => {
        if (!controller.signal.aborted)
          setError(
            cause instanceof Error ? cause.message : "Unable to load streams",
          );
      });
    return () => controller.abort();
  }, [tenant, environment, params]);
  const apply = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const next = new URLSearchParams(params);
    for (const key of ["search", "health", "retention_risk", "sort"]) {
      const value = String(data.get(key) ?? "");
      if (value) next.set(key, value);
      else next.delete(key);
    }
    next.delete("cursor");
    setParams(next);
  };
  return (
    <section aria-labelledby="streams-title" className="page-card">
      <h1 id="streams-title">Streams Inventory</h1>
      <p>
        Tenant-scoped Kafka topics with measured health, lag, retention risk,
        schemas, connectors, and incidents.
      </p>
      <form role="search" onSubmit={apply} className="stream-filters">
        <label>
          Search topics{" "}
          <input
            name="search"
            type="search"
            defaultValue={params.get("search") ?? ""}
          />
        </label>
        <label>
          Health{" "}
          <select name="health" defaultValue={params.get("health") ?? ""}>
            <option value="">All</option>
            <option>healthy</option>
            <option>degraded</option>
            <option>critical</option>
            <option>unknown</option>
          </select>
        </label>
        <label>
          Retention risk{" "}
          <select
            name="retention_risk"
            defaultValue={params.get("retention_risk") ?? ""}
          >
            <option value="">All</option>
            <option>safe</option>
            <option>at_risk</option>
            <option>data_loss_suspected</option>
          </select>
        </label>
        <label>
          Sort{" "}
          <select
            name="sort"
            defaultValue={params.get("sort") ?? "last_observed"}
          >
            <option value="last_observed">Last observed</option>
            <option value="topic">Topic</option>
            <option value="maximum_lag">Maximum lag</option>
            <option value="retention_risk">Retention risk</option>
            <option value="throughput">Throughput</option>
          </select>
        </label>
        <button type="submit">Apply</button>
      </form>
      {error && (
        <div role="alert" className="data-state">
          Unavailable — {error}
        </div>
      )}
      {!result && !error && (
        <div role="status" className="data-state">
          Loading measured Stream evidence…
        </div>
      )}
      {result && (
        <>
          <div role="status" className="data-state">
            {result.data_status} — sources:{" "}
            {result.source_coverage.join(", ") || "none configured"}
          </div>
          <div
            className="table-scroll"
            tabIndex={0}
            aria-label="Scrollable Streams inventory"
          >
            <table>
              <caption>Kafka streams</caption>
              <thead>
                <tr>
                  <th>Topic</th>
                  <th>Cluster</th>
                  <th>Health</th>
                  <th>Max lag</th>
                  <th>Throughput</th>
                  <th>Retention risk</th>
                  <th>Observed</th>
                </tr>
              </thead>
              <tbody>
                {result.items.map((item) => (
                  <tr key={item.stream_id ?? item.name}>
                    <td>
                      <Link
                        to={`/streams/topics/${encodeURIComponent(item.stream_id ?? String(item.name))}`}
                      >
                        {item.topic ?? item.name ?? "Unknown"}
                      </Link>
                    </td>
                    <td>
                      <Link
                        to={`/streams/clusters/${encodeURIComponent(String(item.cluster_id ?? "unknown"))}`}
                      >
                        {String(item.cluster_id ?? "Unknown")}
                      </Link>
                    </td>
                    <td>{item.health ?? "Unknown"}</td>
                    <td>{item.maximum_lag ?? "Unknown"}</td>
                    <td>{item.records_per_second ?? "Unknown"}</td>
                    <td>{item.retention_risk ?? "Unknown"}</td>
                    <td>
                      {item.observed_at
                        ? new Date(item.observed_at).toLocaleString()
                        : "Unknown"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {!result.items.length && (
            <p>No streams match these server-side filters.</p>
          )}
          <nav aria-label="Inventory pagination" className="pagination">
            <button
              disabled={!params.has("cursor")}
              onClick={() => {
                const next = new URLSearchParams(params);
                next.delete("cursor");
                setParams(next);
              }}
            >
              First page
            </button>
            <button
              disabled={!result.next_cursor}
              onClick={() => {
                const next = new URLSearchParams(params);
                if (result.next_cursor) next.set("cursor", result.next_cursor);
                setParams(next);
              }}
            >
              Next
            </button>
          </nav>
        </>
      )}
    </section>
  );
}
