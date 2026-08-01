import {
  qualityCoverage,
  qualityRecommendations,
  qualityRuntimeBacklog,
  qualityRuntimeHealth,
} from "../../api/quality";
import { useProductContext } from "../../state/context";
import {
  display,
  EvidencePanel,
  QualityStatusBanner,
  StatusBadge,
} from "./components/QualityComponents";
import { useQualityRequest } from "./useQualityRequest";
export function QualityAuxiliary({
  section,
}: {
  section: "recommendations" | "coverage" | "runtime";
}) {
  const { tenant, environment } = useProductContext();
  if (section === "recommendations")
    return <Recommendations tenant={tenant} env={environment} />;
  if (section === "coverage")
    return <Coverage tenant={tenant} env={environment} />;
  return <Runtime tenant={tenant} env={environment} />;
}
function Recommendations({ tenant, env }: { tenant: string; env: string }) {
  const r = useQualityRequest(
    (s) => qualityRecommendations(tenant, env, undefined, s),
    [tenant, env],
  );
  return (
    <section>
      <h2>Recommendations</h2>
      <p>Read-only proposals; they are not active monitors.</p>
      {r.loading ? (
        <p role="status">Loading recommendations…</p>
      ) : r.error ? (
        <p role="alert">{r.error}</p>
      ) : r.data?.items.length ? (
        <div className="table-scroll">
          <table>
            <caption>Monitor proposals</caption>
            <thead>
              <tr>
                {[
                  "Recommended monitor type",
                  "Target",
                  "Rationale",
                  "Confidence",
                  "Business priority",
                  "Risk",
                  "Expected compute cost",
                  "Required permissions",
                  "Coverage gap",
                  "State",
                ].map((x) => (
                  <th key={x}>{x}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {r.data.items.map((x) => (
                <tr key={x.id}>
                  <td>{x.monitor_type}</td>
                  <td>{x.target_display_name}</td>
                  <td>{x.rationale}</td>
                  <td>{x.confidence}</td>
                  <td>{x.business_priority}</td>
                  <td>{x.risk}</td>
                  <td>{x.expected_compute_cost}</td>
                  <td>{x.expected_collection_permissions.join(", ")}</td>
                  <td>{x.coverage_gap_closed.join(", ")}</td>
                  <td>{x.state}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p>No recommendation evidence is configured.</p>
      )}
    </section>
  );
}
function Coverage({ tenant, env }: { tenant: string; env: string }) {
  const r = useQualityRequest(
    (s) => qualityCoverage(tenant, env, s),
    [tenant, env],
  );
  if (r.loading) return <p role="status">Loading coverage…</p>;
  if (r.error) return <p role="alert">{r.error}</p>;
  const d = r.data;
  if (!d) return null;
  return (
    <section>
      <h2>Coverage</h2>
      <QualityStatusBanner evidence={d} />
      <p>
        <StatusBadge value={d.state} />
      </p>
      {d.denominator === null ? (
        <p>Coverage denominator is unknown; no percentage is calculated.</p>
      ) : (
        <>
          <p>
            {display(d.numerator)} of {d.denominator} applicable targets are
            covered.
          </p>
          {d.denominator > 0 && d.coverage_percentage !== null && (
            <progress
              max="100"
              value={d.coverage_percentage}
              aria-label="Quality coverage percentage"
            >
              {d.coverage_percentage}%
            </progress>
          )}
        </>
      )}
      <dl className="detail-grid">
        <dt>Percentage</dt>
        <dd>
          {d.state === "not_configured"
            ? "Not configured"
            : display(d.coverage_percentage, "%")}
        </dd>
        <dt>High-risk gaps</dt>
        <dd>{d.high_risk_gaps.join(", ") || "None reported"}</dd>
        <dt>Exclusions</dt>
        <dd>{d.exclusions.join(", ") || "None reported"}</dd>
        <dt>Stale or broken monitors</dt>
        <dd>{d.stale_or_broken_monitors.join(", ") || "None reported"}</dd>
        <dt>Recommendations</dt>
        <dd>{display(d.recommendation_count)}</dd>
      </dl>
      <EvidencePanel evidence={d} />
    </section>
  );
}
function Runtime({ tenant, env }: { tenant: string; env: string }) {
  const health = useQualityRequest(
    (s) => qualityRuntimeHealth(tenant, env, s),
    [tenant, env],
  );
  const backlog = useQualityRequest(
    (s) => qualityRuntimeBacklog(tenant, env, s),
    [tenant, env],
  );
  if (health.loading || backlog.loading)
    return <p role="status">Loading runtime health…</p>;
  if (health.error)
    return (
      <section>
        <h2>Runtime</h2>
        <div role="alert">
          <strong>Runtime unavailable</strong>
          <p>{health.error}</p>
          <p>No healthy-runtime claim can be made without runtime evidence.</p>
        </div>
      </section>
    );
  const d = health.data;
  if (!d) return null;
  return (
    <section>
      <h2>Runtime</h2>
      <QualityStatusBanner evidence={d} />
      <dl className="detail-grid">
        <dt>Runtime state</dt>
        <dd>
          <StatusBadge value={d.state} />
        </dd>
        <dt>Backlog</dt>
        <dd>{display(backlog.data?.backlog ?? d.backlog)}</dd>
        <dt>Worker count</dt>
        <dd>{display(d.worker_count)}</dd>
        <dt>Last heartbeat</dt>
        <dd>{display(d.last_heartbeat)}</dd>
        <dt>Last successful cycle</dt>
        <dd>{display(d.last_successful_cycle)}</dd>
        <dt>Last failed cycle</dt>
        <dd>{display(d.last_failed_cycle)}</dd>
        <dt>Active leases</dt>
        <dd>{display(d.active_leases)}</dd>
        <dt>Expired leases</dt>
        <dd>{display(d.expired_leases)}</dd>
        <dt>Consecutive failures</dt>
        <dd>{display(d.consecutive_failures)}</dd>
        <dt>Next cycle</dt>
        <dd>{display(d.next_cycle_at)}</dd>
      </dl>
      <p>
        This view reports worker evidence only; no runtime controls are
        available.
      </p>
    </section>
  );
}
