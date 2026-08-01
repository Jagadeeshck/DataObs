import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  qualityApi,
  type Coverage,
  type MonitorDefinition,
  type Recommendation,
  type RuntimeHealth,
} from "../../api/quality";
import { useProductContext } from "../../state/context";
import { Evidence, shown } from "./Evidence";

export function QualityOverview() {
  const { tenant, environment } = useProductContext();
  const [monitors, setMonitors] = useState<MonitorDefinition[]>([]);
  const [coverage, setCoverage] = useState<Coverage>({ state: "unknown" });
  const [runtime, setRuntime] = useState<RuntimeHealth>();
  const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    const c = new AbortController();
    Promise.allSettled([
      qualityApi.monitors(
        tenant,
        environment,
        new URLSearchParams({ limit: "50" }),
        c.signal,
      ),
      qualityApi.coverage(tenant, environment, c.signal),
      qualityApi.runtime(tenant, environment, "health", c.signal),
      qualityApi.recommendations(tenant, environment, c.signal),
    ]).then(([m, co, r, re]) => {
      const w: string[] = [];
      if (m.status === "fulfilled") setMonitors(m.value.data.items);
      else w.push("Monitor inventory unavailable");
      if (co.status === "fulfilled") setCoverage(co.value.data);
      else w.push("Coverage has not been calculated");
      if (r.status === "fulfilled") setRuntime(r.value.data);
      else w.push("Runtime health unavailable");
      if (re.status === "fulfilled") setRecommendations(re.value.data.items);
      else w.push("Recommendations unavailable");
      setWarnings(w);
      setLoading(false);
    });
    return () => c.abort();
  }, [tenant, environment]);
  if (loading) return <p role="status">Loading quality evidence…</p>;
  const states = Object.entries(
    monitors.reduce<Record<string, number>>(
      (a, m) => ({ ...a, [m.state]: (a[m.state] ?? 0) + 1 }),
      {},
    ),
  );
  return (
    <section className="quality-page">
      <nav aria-label="Breadcrumb">Home / Quality</nav>
      <div className="quality-heading">
        <div>
          <h1>Data Quality</h1>
          <p>
            Measured monitoring health, coverage, findings and recommendations.
          </p>
        </div>
        <Link className="primary-action" to="/quality/monitors/new">
          Create monitor
        </Link>
      </div>
      {warnings.length > 0 && (
        <aside role="status" className="quality-warning">
          <strong>Partial evidence</strong>
          <ul>
            {warnings.map((x) => (
              <li key={x}>{x}</li>
            ))}
          </ul>
        </aside>
      )}
      <div className="quality-grid">
        <Evidence
          status={coverage.state === "unknown" ? "unknown" : "available"}
        >
          <h2>Coverage</h2>
          <b>
            {coverage.numerator !== undefined &&
            coverage.denominator !== undefined
              ? `${coverage.numerator} / ${coverage.denominator}`
              : "Not calculated"}
          </b>
          <p>{coverage.high_risk_gaps?.length ?? 0} high-risk gaps</p>
        </Evidence>
        <Evidence
          status={runtime ? "available" : "unavailable"}
          timestamp={runtime?.observed_at}
          source={runtime?.provider}
        >
          <h2>Runtime health</h2>
          <b>{shown(runtime?.state)}</b>
          <p>Backlog: {shown(runtime?.backlog)}</p>
        </Evidence>
        <Evidence status="available">
          <h2>Monitors</h2>
          <b>{monitors.length}</b>
          <p>
            {states.map(([s, n]) => `${s}: ${n}`).join(" · ") ||
              "No monitors exist"}
          </p>
        </Evidence>
        <Evidence status="available">
          <h2>Recommendations</h2>
          <b>{recommendations.length}</b>
          <p>
            {coverage.recommendation_count !== undefined
              ? `Coverage reports ${coverage.recommendation_count}`
              : "Coverage count unavailable"}
          </p>
        </Evidence>
      </div>
      <h2>Attention required</h2>
      <ul>
        {coverage.stale_or_broken_monitors?.map((id) => (
          <li key={id}>
            <Link to={`/quality/monitors/${encodeURIComponent(id)}`}>{id}</Link>{" "}
            — stale or broken
          </li>
        ))}
        {!coverage.stale_or_broken_monitors?.length && (
          <li>No stale or broken monitor was reported.</li>
        )}
      </ul>
      <Link to="/quality/monitors">View monitor inventory</Link>
      <Recommendations items={recommendations} />
    </section>
  );
}
function Recommendations({ items }: { items: Recommendation[] }) {
  return (
    <section>
      <h2>Recommendations</h2>
      {items.length === 0 ? (
        <p>No recommendations are available.</p>
      ) : (
        <div className="table-scroll">
          <table>
            <caption>Recommended monitors</caption>
            <thead>
              <tr>
                <th>Type</th>
                <th>Rationale</th>
                <th>Confidence</th>
                <th>Cost</th>
                <th>Risk</th>
                <th>State</th>
              </tr>
            </thead>
            <tbody>
              {items.map((x) => (
                <tr key={x.id}>
                  <th>{x.monitor_type}</th>
                  <td>{x.rationale}</td>
                  <td>{x.confidence}</td>
                  <td>{x.expected_compute_cost}</td>
                  <td>{x.risk}</td>
                  <td>{x.state}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
