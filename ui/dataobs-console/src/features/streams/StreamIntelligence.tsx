import { useEffect, useState } from "react";
import {
  streamIntelligenceApi,
  type IntelligenceSummary,
  type RuntimeHealth,
} from "../../api/streamIntelligence";
import { useProductContext } from "../../state/context";

export function StreamIntelligence() {
  const { tenant, environment } = useProductContext();
  const [summary, setSummary] = useState<IntelligenceSummary>();
  const [runtime, setRuntime] = useState<RuntimeHealth>();
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      streamIntelligenceApi.summary(tenant, environment, controller.signal),
      streamIntelligenceApi.runtime(tenant, environment, controller.signal),
    ])
      .then(([nextSummary, nextRuntime]) => {
        setSummary(nextSummary);
        setRuntime(nextRuntime);
      })
      .catch((cause: unknown) => {
        if (!controller.signal.aborted)
          setError(
            cause instanceof Error
              ? cause.message
              : "Stream intelligence unavailable",
          );
      });
    return () => controller.abort();
  }, [tenant, environment]);
  const cards = [
    ["Active anomalies", "anomalous"],
    ["Severe anomalies", "severe"],
    ["Recovering", "recovering"],
    ["Retention warnings", "retention_warning"],
    ["Exhaustion predictions", "exhaustion_predicted"],
    ["Failure candidates", "failure_candidates"],
    ["Stale detectors", "stale"],
  ] as const;
  return (
    <section className="page-card" aria-labelledby="intelligence-title">
      <h1 id="intelligence-title">Stream Intelligence</h1>
      <p>
        Explainable anomaly and retention evidence. Missing evidence is shown as
        unavailable, never as zero. Failure findings are candidates, not
        confirmed message corruption.
      </p>
      {error && <p role="alert">{error}</p>}
      <div className="metric-grid" aria-label="Stream intelligence overview">
        {cards.map(([label, key]) => (
          <article key={key}>
            <h2>{label}</h2>
            <strong>{summary ? (summary.counts[key] ?? 0) : "—"}</strong>
          </article>
        ))}
        <article>
          <h2>Runtime health</h2>
          <strong>
            {runtime?.configured ? runtime.lease_status : "Not configured"}
          </strong>
        </article>
      </div>
      <h2>Anomaly evidence</h2>
      <p>
        No detector does not mean normal. Select an enabled detector to inspect
        observed series, expected baseline, expected range and nearby correlated
        changes.
      </p>
      <div className="table-scroll">
        <table>
          <caption>
            Accessible text alternative for observed and baseline charts
          </caption>
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Observed</th>
              <th>Expected</th>
              <th>Range</th>
              <th>State</th>
              <th>Method</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td colSpan={6}>No evaluated evidence available</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  );
}
