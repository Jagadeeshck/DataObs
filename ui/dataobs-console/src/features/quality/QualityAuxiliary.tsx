import { qualityApi, type Recommendation } from "../../api/quality";
import { useCallback, useEffect, useState } from "react";
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
  const [items, setItems] = useState<Recommendation[]>([]);
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState<string>();
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const load = useCallback(
    (signal?: AbortSignal) =>
      qualityApi.recommendations(tenant, env, signal).then((result) => {
        setItems(result.data.items);
        setLoading(false);
      }),
    [tenant, env],
  );
  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal).catch((e: Error) => {
      if (e.name !== "AbortError") {
        setError(e.message);
        setLoading(false);
      }
    });
    return () => controller.abort();
  }, [load]);
  const decide = async (
    item: Recommendation,
    action: "accept" | "reject" | "defer",
  ) => {
    if (pending || !confirm(`${action} recommendation ${item.id}?`)) return;
    setPending(item.id);
    setError("");
    setMessage("");
    try {
      const result = await qualityApi.mutate<{ state?: string }>(
        tenant,
        env,
        `/recommendations/${encodeURIComponent(item.id)}/${action}`,
        {},
      );
      setMessage(
        `Decision recorded${result.data.state ? `: ${result.data.state}` : ""}. No monitor creation is implied.`,
      );
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setPending(undefined);
    }
  };
  return (
    <section>
      <h2>Recommendations</h2>
      <p>
        Proposals are not active monitors. Decisions do not imply monitor
        creation.
      </p>
      {message && <p role="status">{message}</p>}
      {error && <p role="alert">{error}</p>}
      {loading ? (
        <p role="status">Loading recommendations…</p>
      ) : items.length ? (
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
                  "Duplicate analysis",
                  "Proposed baseline / safety threshold",
                  "State",
                  "Decision",
                ].map((x) => (
                  <th key={x}>{x}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {items.map((x) => (
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
                  <td>{x.duplication_analysis}</td>
                  <td>
                    <code>
                      {JSON.stringify(
                        x.proposed_baseline ??
                          x.proposed_fixed_safety_threshold ??
                          "Not proposed",
                      )}
                    </code>
                  </td>
                  <td>{x.state}</td>
                  <td>
                    {(["accepted", "rejected"] as string[]).includes(x.state)
                      ? "Terminal"
                      : (["accept", "reject", "defer"] as const).map(
                          (action) => (
                            <button
                              key={action}
                              disabled={Boolean(pending)}
                              onClick={() => void decide(x, action)}
                            >
                              {action}
                            </button>
                          ),
                        )}
                  </td>
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
    (s) => qualityApi.coverage(tenant, env, s).then((x) => x.data),
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
    (s) => qualityApi.runtime(tenant, env, "health", s).then((x) => x.data),
    [tenant, env],
  );
  const backlog = useQualityRequest(
    (s) => qualityApi.runtime(tenant, env, "backlog", s).then((x) => x.data),
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
