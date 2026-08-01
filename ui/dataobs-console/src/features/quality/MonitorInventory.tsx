import { Link, useSearchParams } from "react-router-dom";
import { qualityMonitors } from "../../api/quality";
import { useProductContext } from "../../state/context";
import {
  display,
  QualityStatusBanner,
  StatusBadge,
} from "./components/QualityComponents";
import { useQualityRequest } from "./useQualityRequest";
const filters = [
  ["search", "Search"],
  ["state", "State"],
  ["monitor_type", "Monitor type"],
  ["threshold_mode", "Threshold mode"],
  ["managed_by", "Managed by"],
  ["creation_source", "Creation source"],
  ["source_type", "Source type"],
];
export function MonitorInventory() {
  const { tenant, environment } = useProductContext();
  const [params, setParams] = useSearchParams();
  const query = new URLSearchParams(params);
  query.delete("tab");
  const key = query.toString();
  const { data, error, loading, refresh } = useQualityRequest(
    (s) => qualityMonitors(tenant, environment, query, s),
    [tenant, environment, key],
  );
  const update = (k: string, v: string) => {
    const n = new URLSearchParams(params);
    if (v) n.set(k, v);
    else n.delete(k);
    n.delete("cursor");
    setParams(n);
  };
  return (
    <section aria-labelledby="monitor-inventory">
      <h2 id="monitor-inventory">Monitor inventory</h2>
      <form
        className="quality-filters"
        onSubmit={(e) => e.preventDefault()}
        aria-label="Monitor filters"
      >
        {filters.map(([k, l]) => (
          <label key={k}>
            {l}
            <input
              value={params.get(k) ?? ""}
              onChange={(e) => update(k, e.target.value)}
            />
          </label>
        ))}
        {[
          ["has_open_findings", "Open findings"],
          ["has_incident", "Incident linked"],
          ["is_stale", "Stale"],
        ].map(([k, l]) => (
          <label key={k}>
            {l}
            <select
              value={params.get(k) ?? ""}
              onChange={(e) => update(k, e.target.value)}
            >
              <option value="">Any</option>
              <option value="true">Yes</option>
              <option value="false">No</option>
            </select>
          </label>
        ))}
        <label>
          Sort
          <select
            value={params.get("sort") ?? "last_updated"}
            onChange={(e) => update("sort", e.target.value)}
          >
            {[
              "name",
              "last_updated",
              "state",
              "monitor_type",
              "last_observation",
              "last_evaluation",
              "open_findings",
              "severity",
            ].map((x) => (
              <option key={x}>{x}</option>
            ))}
          </select>
        </label>
        <button
          type="button"
          onClick={() => {
            const n = new URLSearchParams();
            n.set("tab", "monitors");
            setParams(n);
          }}
        >
          Clear all
        </button>
        <button type="button" onClick={refresh}>
          Refresh
        </button>
      </form>
      {loading && <p role="status">Loading monitors…</p>}
      {error && <p role="alert">{error}</p>}
      {data && (
        <>
          <QualityStatusBanner evidence={data} />
          {!data.items.length ? (
            <p>No monitors match these filters.</p>
          ) : (
            <div className="table-scroll">
              <table>
                <caption>Quality monitors and measured evidence</caption>
                <thead>
                  <tr>
                    {[
                      "Monitor",
                      "Type",
                      "Target",
                      "State",
                      "Schedule",
                      "Threshold",
                      "Last value",
                      "Last evaluation",
                      "Anomaly score",
                      "Open findings",
                      "Severity",
                      "Incident",
                      "Cold-start state",
                      "Observed",
                    ].map((x) => (
                      <th key={x}>{x}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((m) => (
                    <tr key={m.id}>
                      <th>
                        <Link
                          to={`/quality/monitors/${encodeURIComponent(m.id)}`}
                        >
                          {m.name}
                        </Link>
                        {m.stale && <span className="stale-label"> Stale</span>}
                      </th>
                      <td>{m.monitor_type}</td>
                      <td>{m.target_display_name}</td>
                      <td>
                        <StatusBadge value={m.state} />
                      </td>
                      <td>{m.schedule_interval}</td>
                      <td>{m.threshold_mode}</td>
                      <td>
                        {display(m.last_value, m.unit ? ` ${m.unit}` : "")}
                      </td>
                      <td>{display(m.last_evaluation_status)}</td>
                      <td>{display(m.anomaly_score)}</td>
                      <td>{display(m.open_finding_count)}</td>
                      <td>{display(m.highest_open_severity)}</td>
                      <td>{display(m.incident_count)}</td>
                      <td>{display(m.cold_start_state)}</td>
                      <td>{display(m.last_observation_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {data.next_cursor && (
            <button onClick={() => update("cursor", data.next_cursor!)}>
              Next page
            </button>
          )}
        </>
      )}
    </section>
  );
}
