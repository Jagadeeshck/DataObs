import { useEffect, useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, type StreamList } from "../../api/client";
import {
  DataStatusBanner,
  EmptyState,
  HealthBadge,
  MetricCard,
  UnavailableState,
  display,
} from "./components";
import { useProductContext } from "../../state/context";
import { MessagingOverview } from "./MessagingOverview";

export function StreamsInventory() {
  const { tenant, environment } = useProductContext();
  const [params, setParams] = useSearchParams();
  const [result, setResult] = useState<StreamList>();
  const [error, setError] = useState("");
  const [refresh, setRefresh] = useState(0);
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
  }, [tenant, environment, params, refresh]);
  const apply = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const next = new URLSearchParams(params);
    for (const key of [
      "search",
      "cluster_id",
      "health",
      "retention_risk",
      "has_lag",
      "freshness",
      "sort",
    ]) {
      const value = String(data.get(key) ?? "");
      if (value) next.set(key, value);
      else next.delete(key);
    }
    next.delete("cursor");
    setParams(next);
  };
  return (
    <>
      <section className="page-card">
        <MessagingOverview />
      </section>
      <section aria-labelledby="streams-title" className="page-card">
        <h1 id="streams-title">Streams Inventory</h1>
        <p>
          Kafka topic inventory (legacy-compatible). Non-Kafka inventories
          appear only when bounded provider APIs are available.
        </p>
        <form role="search" onSubmit={apply} className="stream-filters">
          <label>
            Cluster{" "}
            <input
              name="cluster_id"
              defaultValue={params.get("cluster_id") ?? ""}
            />
          </label>
          <label>
            Search topics{" "}
            <input
              name="search"
              type="search"
              defaultValue={params.get("search") ?? ""}
            />
          </label>
          <label>
            Has lag{" "}
            <select name="has_lag" defaultValue={params.get("has_lag") ?? ""}>
              <option value="">All</option>
              <option value="true">With consumer lag</option>
              <option value="false">No measured lag</option>
            </select>
          </label>
          <label>
            Observed freshness{" "}
            <select
              name="freshness"
              defaultValue={params.get("freshness") ?? ""}
            >
              <option value="">Any</option>
              <option value="fresh">Fresh</option>
              <option value="stale">Stale</option>
            </select>
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
          <button type="button" onClick={() => setParams({})}>
            Clear all
          </button>
          <button
            type="button"
            onClick={() => setRefresh((value) => value + 1)}
          >
            Refresh
          </button>
        </form>
        {error && <UnavailableState message={error} />}
        {!result && !error && (
          <div role="status" className="data-state">
            Loading measured Stream evidence…
          </div>
        )}
        {result && (
          <>
            <DataStatusBanner
              status={result.data_status}
              warnings={result.warnings}
            />
            <p>
              <strong>Bounded page summary</strong> (not global totals)
            </p>
            <div className="metric-grid">
              <MetricCard label="Visible on page" value={result.items.length} />
              <MetricCard
                label="Healthy"
                value={
                  result.items.filter((x) => x.health === "healthy").length
                }
              />
              <MetricCard
                label="Warning / degraded"
                value={
                  result.items.filter((x) =>
                    ["warning", "degraded"].includes(x.health ?? ""),
                  ).length
                }
              />
              <MetricCard
                label="Critical"
                value={
                  result.items.filter((x) => x.health === "critical").length
                }
              />
              <MetricCard
                label="Unknown"
                value={
                  result.items.filter(
                    (x) => !x.health || x.health === "unknown",
                  ).length
                }
              />
              <MetricCard
                label="At retention risk"
                value={
                  result.items.filter((x) => x.retention_risk === "at_risk")
                    .length
                }
              />
              <MetricCard
                label="Suspected data loss"
                value={
                  result.items.filter(
                    (x) => x.retention_risk === "data_loss_suspected",
                  ).length
                }
              />
              <MetricCard
                label="With consumer lag"
                value={
                  result.items.filter((x) => (x.maximum_lag ?? 0) > 0).length
                }
              />
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
                    <th>Partitions</th>
                    <th>Replication</th>
                    <th>Producer rate</th>
                    <th>Consumer rate</th>
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
                      <td>
                        <HealthBadge health={item.health} />
                      </td>
                      <td>{display(item.partition_count)}</td>
                      <td>
                        {display(item.replication_factor, "Not configured")}
                      </td>
                      <td>{display(item.producer_rate)}</td>
                      <td>{display(item.consumer_rate)}</td>
                      <td>{display(item.maximum_lag)}</td>
                      <td>{display(item.records_per_second)}</td>
                      <td>{display(item.retention_risk, "Not configured")}</td>
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
              <EmptyState>
                No streams match these server-side filters.
              </EmptyState>
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
                  if (result.next_cursor)
                    next.set("cursor", result.next_cursor);
                  setParams(next);
                }}
              >
                Next
              </button>
            </nav>
          </>
        )}
      </section>
    </>
  );
}
