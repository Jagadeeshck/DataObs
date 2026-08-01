import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useSearchParams } from "react-router-dom";
import {
  reliabilityApi,
  type ReliabilityDefinition,
  type RuntimeHealth,
} from "../../api/reliability";
import { useProductContext } from "../../state/context";

export function StreamsReliability() {
  const { tenant, environment } = useProductContext();
  const [params, setParams] = useSearchParams();
  const [items, setItems] = useState<ReliabilityDefinition[]>([]);
  const [runtime, setRuntime] = useState<RuntimeHealth>();
  const [error, setError] = useState("");
  const [refresh, setRefresh] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    const query = new URLSearchParams(params);
    query.set("limit", "100");
    Promise.all([
      reliabilityApi.definitions(tenant, environment, query, controller.signal),
      reliabilityApi.runtime(tenant, environment, controller.signal),
    ])
      .then(([page, health]) => {
        setItems(page.items);
        setRuntime(health);
      })
      .catch((cause: unknown) => {
        if (!controller.signal.aborted)
          setError(
            cause instanceof Error ? cause.message : "Reliability unavailable",
          );
      });
    return () => controller.abort();
  }, [tenant, environment, params, refresh]);
  const counts = useMemo(
    () =>
      items.reduce<Record<string, number>>((all, item) => {
        const status = item.latest_evaluation_id
          ? "evaluated"
          : item.enabled
            ? "awaiting evaluation"
            : "disabled";
        all[status] = (all[status] ?? 0) + 1;
        return all;
      }, {}),
    [items],
  );
  const filter = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const next = new URLSearchParams();
    ["resource_type", "metric", "status", "owner", "enabled"].forEach((key) => {
      const value = String(form.get(key) ?? "");
      if (value) next.set(key, value);
    });
    setParams(next);
  };
  return (
    <section className="page-card" aria-labelledby="reliability-title">
      <h1 id="reliability-title">Stream Reliability</h1>
      <p>
        Measured evidence remains distinct from missing and stale observations.
        Estimated pathway latency is labelled by its evidence method.
      </p>
      {error && <p role="alert">{error}</p>}
      <div className="metric-grid" aria-label="Reliability summary">
        <article>
          <h2>Active objectives</h2>
          <strong>{items.filter((x) => x.enabled).length}</strong>
        </article>
        <article>
          <h2>Awaiting evaluation</h2>
          <strong>{counts["awaiting evaluation"] ?? 0}</strong>
        </article>
        <article>
          <h2>Disabled drafts</h2>
          <strong>{counts.disabled ?? 0}</strong>
        </article>
        <article>
          <h2>Runtime</h2>
          <strong>
            {runtime?.configured ? runtime.lease_state : "Not configured"}
          </strong>
          <p>
            Latest success:{" "}
            {runtime?.latest_successful_evaluation ?? "No evaluation recorded"}
          </p>
        </article>
      </div>
      <form role="search" onSubmit={filter} className="stream-filters">
        <label>
          Resource type{" "}
          <select
            name="resource_type"
            defaultValue={params.get("resource_type") ?? ""}
          >
            <option value="">All</option>
            <option value="kafka_cluster">Cluster</option>
            <option value="topic">Topic</option>
            <option value="consumer_group">Consumer group</option>
            <option value="connector">Connector</option>
            <option value="pathway">Pathway</option>
          </select>
        </label>
        <label>
          Metric{" "}
          <input name="metric" defaultValue={params.get("metric") ?? ""} />
        </label>
        <label>
          Status{" "}
          <input name="status" defaultValue={params.get("status") ?? ""} />
        </label>
        <label>
          Owner <input name="owner" defaultValue={params.get("owner") ?? ""} />
        </label>
        <label>
          Enabled{" "}
          <select name="enabled" defaultValue={params.get("enabled") ?? ""}>
            <option value="">All</option>
            <option value="true">Enabled</option>
            <option value="false">Disabled</option>
          </select>
        </label>
        <button type="submit">Apply filters</button>
        <button type="button" onClick={() => setRefresh((x) => x + 1)}>
          Refresh
        </button>
      </form>
      <div className="table-scroll">
        <table>
          <caption>
            Reliability definitions and text alternative for objective state
          </caption>
          <thead>
            <tr>
              <th>Resource</th>
              <th>Metric</th>
              <th>Status</th>
              <th>Threshold</th>
              <th>Window</th>
              <th>Owner</th>
              <th>Enabled</th>
              <th>Evaluation</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id}>
                <td>
                  {item.resource_type}: {item.resource_id}
                </td>
                <td>{item.metric}</td>
                <td>
                  {item.latest_evaluation_id
                    ? "Evaluated"
                    : item.enabled
                      ? "Awaiting first evaluation"
                      : "Disabled"}
                </td>
                <td>
                  {item.operator} {String(item.threshold)}
                </td>
                <td>{item.evaluation_window_seconds}s</td>
                <td>{item.owner}</td>
                <td>{item.enabled ? "Yes" : "No"}</td>
                <td>{item.latest_evaluation_id ?? "No evidence"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
