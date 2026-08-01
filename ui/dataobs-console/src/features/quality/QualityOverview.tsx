import { qualityOverview } from "../../api/quality";
import { useProductContext } from "../../state/context";
import {
  display,
  MissingEvidencePanel,
  QualityMetricCard,
  QualityStatusBanner,
  StatusBadge,
} from "./components/QualityComponents";
import { useQualityRequest } from "./useQualityRequest";
export function QualityOverviewView() {
  const { tenant, environment } = useProductContext();
  const { data, error, loading, refresh } = useQualityRequest(
    (s) => qualityOverview(tenant, environment, s),
    [tenant, environment],
  );
  if (loading) return <p role="status">Loading quality overview…</p>;
  if (error)
    return (
      <div role="alert">
        <p>{error}</p>
        <button onClick={refresh}>Retry</button>
      </div>
    );
  if (!data) return null;
  const cards = [
    ...["monitor_count", "Total monitors"],
    ["active_monitor_count", "Active monitors"],
    ["learning_monitor_count", "Learning monitors"],
    ["degraded_monitor_count", "Degraded monitors"],
    ["error_monitor_count", "Error monitors"],
    ["stale_monitor_count", "Stale monitors"],
    ["open_finding_count", "Open findings"],
    ["critical_finding_count", "Critical findings"],
    ["coverage_percentage", "Coverage"],
    ["runtime_backlog", "Runtime backlog"],
  ] as [keyof typeof data, string][];
  return (
    <div>
      <QualityStatusBanner evidence={data} />
      <button onClick={refresh}>Refresh evidence</button>
      <div className="metric-grid">
        {cards.map(([key, label]) => (
          <QualityMetricCard
            key={key as string}
            label={label}
            value={display(
              data[key],
              key === "coverage_percentage" && data[key] !== null ? "%" : "",
            )}
          />
        ))}
      </div>
      <section>
        <h2>Monitor state distribution</h2>
        <p aria-label="Monitor state summary">
          Enabled {data.enabled_monitor_count}; active{" "}
          {data.active_monitor_count}; learning {data.learning_monitor_count};
          degraded {data.degraded_monitor_count}; error{" "}
          {data.error_monitor_count}; suppressed {data.suppressed_monitor_count}
          ; archived {data.archived_monitor_count}.
        </p>
        <table>
          <caption>Monitor states (count)</caption>
          <thead>
            <tr>
              <th>State</th>
              <th>Count</th>
            </tr>
          </thead>
          <tbody>
            {[
              "active",
              "learning",
              "degraded",
              "error",
              "suppressed",
              "archived",
            ].map((x) => (
              <tr key={x}>
                <th>
                  <StatusBadge value={x} />
                </th>
                <td>
                  {data[`${x}_monitor_count` as keyof typeof data] as number}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      <section>
        <h2>Coverage and runtime</h2>
        <dl className="detail-grid">
          <dt>Coverage state</dt>
          <dd>{display(data.coverage_state)}</dd>
          <dt>Exact coverage</dt>
          <dd>
            {display(data.coverage_numerator)} /{" "}
            {display(data.coverage_denominator)}
          </dd>
          <dt>High-risk gaps</dt>
          <dd>{display(data.high_risk_gap_count)}</dd>
          <dt>Runtime state</dt>
          <dd>
            <StatusBadge value={data.runtime_state} />
          </dd>
          <dt>Runtime backlog</dt>
          <dd>{display(data.runtime_backlog)}</dd>
          <dt>Recommendations</dt>
          <dd>{display(data.recommendation_count)}</dd>
        </dl>
      </section>
      <MissingEvidencePanel evidence={data} />
    </div>
  );
}
