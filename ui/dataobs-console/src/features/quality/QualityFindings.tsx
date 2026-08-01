import { Link, useSearchParams } from "react-router-dom";
import { qualityFindings } from "../../api/quality";
import { useProductContext } from "../../state/context";
import {
  display,
  QualityStatusBanner,
  StatusBadge,
} from "./components/QualityComponents";
import { useQualityRequest } from "./useQualityRequest";
export function QualityFindings() {
  const { tenant, environment } = useProductContext();
  const [params, setParams] = useSearchParams();
  const query = new URLSearchParams(params);
  query.delete("tab");
  const key = query.toString();
  const { data, error, loading, refresh } = useQualityRequest(
    (s) => qualityFindings(tenant, environment, query, s),
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
    <section>
      <h2>Findings</h2>
      <form
        className="quality-filters"
        onSubmit={(e) => e.preventDefault()}
        aria-label="Finding filters"
      >
        {[
          "state",
          "severity",
          "monitor_id",
          "asset_id",
          "incident_id",
          "start",
          "end",
        ].map((k) => (
          <label key={k}>
            {k.replaceAll("_", " ")}
            <input
              value={params.get(k) ?? ""}
              onChange={(e) => update(k, e.target.value)}
            />
          </label>
        ))}
        <label>
          Sort
          <select
            value={params.get("sort") ?? "newest"}
            onChange={(e) => update("sort", e.target.value)}
          >
            {["newest", "oldest", "severity", "state"].map((x) => (
              <option key={x}>{x}</option>
            ))}
          </select>
        </label>
        <button type="button" onClick={refresh}>
          Refresh
        </button>
      </form>
      {loading && <p role="status">Loading findings…</p>}
      {error && <p role="alert">{error}</p>}
      {data && (
        <>
          <QualityStatusBanner evidence={data} />
          {data.items.length === 0 ? (
            <p>No measured findings match these filters.</p>
          ) : (
            <div className="table-scroll">
              <table>
                <caption>
                  Quality findings; relationship labels do not imply causality
                </caption>
                <thead>
                  <tr>
                    {[
                      "Finding",
                      "Monitor",
                      "Target",
                      "State",
                      "Severity",
                      "Evaluation",
                      "Incident",
                      "Baseline",
                      "Opened",
                      "Updated",
                    ].map((x) => (
                      <th key={x}>{x}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((f) => (
                    <tr key={f.finding_id}>
                      <th>{f.finding_id}</th>
                      <td>
                        <Link
                          to={`/quality/monitors/${encodeURIComponent(f.monitor_id)}?tab=findings`}
                        >
                          {f.monitor_name ?? f.monitor_id}
                        </Link>
                      </td>
                      <td>{display(f.target_display_name)}</td>
                      <td>
                        <StatusBadge value={f.state} />
                      </td>
                      <td>
                        <StatusBadge value={f.severity} />
                      </td>
                      <td>{f.evaluation_id}</td>
                      <td>
                        {f.incident_id ? (
                          <>
                            <Link
                              to={`/incidents/${encodeURIComponent(f.incident_id)}`}
                            >
                              {f.incident_id}
                            </Link>{" "}
                            ({f.relationship})
                          </>
                        ) : (
                          "Not linked"
                        )}
                      </td>
                      <td>{display(f.baseline_version)}</td>
                      <td>{display(f.opened_at)}</td>
                      <td>{display(f.updated_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </section>
  );
}
