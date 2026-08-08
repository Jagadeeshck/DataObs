import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api, ApiError } from "../../api";
import type {
  CommandCenter as CommandCenterModel,
  PriorityItem,
} from "../../api/types";
import {
  DataStatusBanner,
  EmptyState,
  ErrorState,
  HealthBadge,
  LoadingSkeleton,
  MetricCard,
} from "../../components/Evidence";
import { timeRangeBounds, useProductContext } from "../../state/context";
import { useAbortableRequest } from "../../hooks/useAbortableRequest";

const unknown = "Unknown";
const itemLink = (item: PriorityItem) =>
  item.href ??
  (item.id.startsWith("inc")
    ? `/incidents/${encodeURIComponent(item.id)}`
    : `/flow?entity=${encodeURIComponent(item.entity)}`);
export function CommandCenter() {
  const { tenant, environment, timeRange, refreshGeneration, identity } =
    useProductContext();
  const request = useAbortableRequest();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const [data, setData] = useState<CommandCenterModel>();
  const [error, setError] = useState<ApiError | Error>();
  const [loading, setLoading] = useState(true);
  const load = useCallback(() => {
    if (!tenant || !environment) return;
    setLoading(true);
    setError(undefined);
    void request((signal) =>
      api.commandCenter(
        tenant,
        environment,
        timeRangeBounds(timeRange),
        signal,
      ),
    )
      .then(setData)
      .catch((reason: unknown) => {
        if ((reason as Error).name !== "AbortError") setError(reason as Error);
      })
      .finally(() => setLoading(false));
  }, [environment, request, tenant, timeRange]);
  // The effect deliberately starts an abortable external API synchronisation.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(load, [load, refreshGeneration]);
  const pillar = params.get("pillar") ?? "all";
  const severity = params.get("severity") ?? "all";
  const updateFilter = (key: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value === "all") next.delete(key);
    else next.set(key, value);
    setParams(next);
  };
  const queue = (data?.priority_items ?? [])
    .filter(
      (item) =>
        (severity === "all" || item.severity.toLowerCase() === severity) &&
        (pillar === "all" || item.service === pillar),
    )
    .slice(0, 50);
  if (loading && !data)
    return (
      <div className="page">
        <LoadingSkeleton label="Loading operational evidence…" />
      </div>
    );
  if (error && !data)
    return (
      <div className="page">
        <h1>Command Center</h1>
        <ErrorState
          message="Operational evidence is unavailable."
          requestId={error instanceof ApiError ? error.requestId : undefined}
          retry={load}
        />
      </div>
    );
  if (!data) return null;
  const evidenceState = data.data_status.complete
    ? data.overall_health
    : "partial";
  return (
    <div className="page">
      <div className="eyebrow">
        COMMAND CENTER <span>/</span> OPERATIONAL EVIDENCE
      </div>
      <div className="page-title">
        <div>
          <h1>Command Center</h1>
          <p>
            Evidence for{" "}
            {identity?.displayName ?? "the current authenticated context"};
            missing signals remain unknown.
          </p>
        </div>
        <div className="actions">
          <Link className="button" to="/dashboards">
            Open operational dashboards
          </Link>
          <button onClick={() => navigator.clipboard?.writeText(location.href)}>
            ↗ Copy share link
          </button>
          <button className="primary" onClick={() => navigate("/flow")}>
            Explore data flow →
          </button>
        </div>
      </div>
      {(error || !data.data_status.complete) && (
        <DataStatusBanner
          state="partial"
          requestId={error instanceof ApiError ? error.requestId : undefined}
        >
          {error
            ? "A refresh failed; previously loaded evidence remains visible."
            : data.data_status.warnings.join(" · ") ||
              "Some required evidence is missing."}
        </DataStatusBanner>
      )}
      <section className={`hero ${evidenceState}`}>
        <div className="hero-state">
          <div>
            <small>OVERALL ESTATE STATE</small>
            <h2>
              <HealthBadge state={evidenceState} />
            </h2>
            <p>
              {data.data_status.complete
                ? "Derived from the available capability evidence."
                : "Overall state is partial; it is not reported as healthy."}
            </p>
          </div>
        </div>
        <div className="hero-metrics">
          <MetricCard
            label="Critical incidents"
            value={data.critical_incidents}
          />
          <MetricCard
            label="Affected services"
            value={data.affected_services}
          />
          <MetricCard
            label="Source coverage"
            value={
              data.data_status.source_coverage == null
                ? null
                : `${data.data_status.source_coverage}%`
            }
          />
          <MetricCard
            label="Last observed"
            value={
              data.data_status.observed_at
                ? new Date(data.data_status.observed_at).toLocaleString()
                : null
            }
          />
        </div>
      </section>
      <div className="section-head">
        <div>
          <h2>Health across six pillars</h2>
          <p>Measured zero is shown as 0; missing values are Unknown.</p>
        </div>
        <label>
          Pillar{" "}
          <select
            value={pillar}
            onChange={(event) => updateFilter("pillar", event.target.value)}
          >
            <option value="all">All pillars</option>
            {data.pillars.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </label>
      </div>
      <section className="pillars">
        {data.pillars
          .filter((item) => pillar === "all" || item.id === pillar)
          .map((item) => (
            <Link
              key={item.id}
              className={`pillar ${item.health}`}
              to={`/flow?pillar=${encodeURIComponent(item.id)}`}
            >
              <div>
                <HealthBadge state={item.health} />
                <em>{item.trend ?? "No trend evidence"}</em>
              </div>
              <h3>{item.name}</h3>
              <strong>{item.metric ?? unknown}</strong>
              <p>
                {item.observed_at
                  ? `Observed ${new Date(item.observed_at).toLocaleString()}`
                  : "Observation time unknown"}
              </p>
              <footer>
                <span>{item.coverage ?? unknown}</span>
                <b>
                  {item.issues == null
                    ? "Issues unknown"
                    : `${item.issues} issues`}
                </b>
              </footer>
            </Link>
          ))}
      </section>
      <section className="panel queue">
        <div className="section-head">
          <div>
            <h2>Priority work queue</h2>
            <p>
              Bounded server evidence; impact and ownership are never inferred.
            </p>
          </div>
          <label>
            Severity{" "}
            <select
              value={severity}
              onChange={(event) => updateFilter("severity", event.target.value)}
            >
              <option value="all">All</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="warning">Warning</option>
            </select>
          </label>
        </div>
        {queue.length ? (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Problem</th>
                  <th>Entity</th>
                  <th>Owner</th>
                  <th>Started</th>
                  <th>Severity</th>
                  <th>Impact</th>
                  <th>Automation</th>
                </tr>
              </thead>
              <tbody>
                {queue.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <Link to={itemLink(item)}>{item.problem}</Link>
                    </td>
                    <td>{item.entity}</td>
                    <td>{item.owner ?? unknown}</td>
                    <td>{item.started ?? unknown}</td>
                    <td>{item.severity}</td>
                    <td>{item.impact ?? unknown}</td>
                    <td>{item.automation ?? "Not available"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState title="No priority work matches these filters" />
        )}
      </section>
      {data.recent_changes.length > 0 && (
        <section className="panel changes">
          <h2>Recent changes</h2>
          {data.recent_changes.map((change) => (
            <article key={change.id}>
              <div>
                <b>{change.title}</b>
                <p>{change.detail}</p>
              </div>
              <time>{change.time}</time>
            </article>
          ))}
        </section>
      )}
      {data.data_status.missing_inputs?.length ||
      data.data_status.warnings.length ? (
        <DataStatusBanner state="partial">
          Missing inputs:{" "}
          {[
            ...(data.data_status.missing_inputs ?? []),
            ...data.data_status.warnings,
          ].join(", ")}
          . <Link to="/integrations">Review integrations</Link>
        </DataStatusBanner>
      ) : null}
    </div>
  );
}
