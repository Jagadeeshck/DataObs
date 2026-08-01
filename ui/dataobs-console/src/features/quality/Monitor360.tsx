import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ApiError } from "../../api/common";
import {
  qualityApi,
  type Evaluation,
  type Finding,
  type MonitorDefinition,
  type Observation,
  type Suppression,
} from "../../api/quality";
import { useProductContext } from "../../state/context";
import { shown } from "./Evidence";
const sections = [
  "overview",
  "configuration",
  "observations",
  "baselines",
  "evaluations",
  "findings",
  "incidents",
  "history",
  "suppressions",
  "runtime",
] as const;
export function Monitor360() {
  const { monitorId = "" } = useParams();
  const { tenant, environment } = useProductContext();
  const [monitor, setMonitor] = useState<MonitorDefinition>();
  const [etag, setEtag] = useState("");
  const [tab, setTab] = useState<(typeof sections)[number]>("overview");
  const [items, setItems] = useState<unknown[]>([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [resetReason, setResetReason] = useState("");
  const [suppression, setSuppression] = useState({
    starts_at: "",
    ends_at: "",
    reason: "",
    approval_reference: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const load = useCallback(
    () =>
      qualityApi
        .monitor(tenant, environment, monitorId)
        .then((x) => {
          setMonitor(x.data);
          setEtag(x.etag ?? x.data.etag);
          setError("");
        })
        .catch((e: Error) => setError(e.message)),
    [tenant, environment, monitorId],
  );
  useEffect(() => {
    void load();
  }, [load]);
  useEffect(() => {
    if (["overview", "configuration", "runtime"].includes(tab)) {
      return;
    }
    const apiSection = tab === "history" ? "history" : tab;
    const c = new AbortController();
    qualityApi
      .section(tenant, environment, monitorId, apiSection, c.signal)
      .then((x) => setItems(x.data.items))
      .catch((e: Error) => setError(e.message));
    return () => c.abort();
  }, [tenant, environment, monitorId, tab]);
  const action = async (kind: string) => {
    if (!monitor) return;
    if (
      ["archive", "enable", "disable"].includes(kind) &&
      !confirm(`${kind} this monitor?`)
    )
      return;
    try {
      if (kind === "run") {
        const x = await qualityApi.mutate<{
          execution_id: string;
          status: string;
        }>(
          tenant,
          environment,
          `/monitors/${encodeURIComponent(monitor.id)}/run`,
          {},
          { "Idempotency-Key": crypto.randomUUID() },
        );
        setMessage(
          `Execution ${x.data.execution_id} is ${x.data.status}. Queued does not mean completed.`,
        );
      } else {
        await qualityApi.mutate(
          tenant,
          environment,
          `/monitors/${encodeURIComponent(monitor.id)}/${kind}`,
          {},
          { "If-Match": etag },
        );
        setMessage(`Monitor ${kind} request succeeded.`);
        await load();
      }
    } catch (e) {
      if (e instanceof ApiError && e.status === 412) {
        setMessage(
          "The monitor changed in another session. Refreshed current definition; review it before trying again.",
        );
        await load();
      } else setError((e as Error).message);
    }
  };
  const refreshSection = async (section: string) => {
    const result = await qualityApi.section(
      tenant,
      environment,
      monitorId,
      section,
    );
    setItems(result.data.items);
  };
  const resetBaseline = async () => {
    if (
      !resetReason.trim() ||
      submitting ||
      !confirm("Reset this monitor baseline?")
    )
      return;
    setSubmitting(true);
    setError("");
    try {
      const result = await qualityApi.mutate<Record<string, unknown>>(
        tenant,
        environment,
        `/monitors/${encodeURIComponent(monitorId)}/baselines/reset`,
        { reason: resetReason.trim() },
        { "If-Match": etag },
      );
      setMessage(
        `Baseline reset recorded: ${JSON.stringify(result.data)}. Historical deletion is not implied.`,
      );
      setResetReason("");
      await refreshSection("baselines");
    } catch (e) {
      if (e instanceof ApiError && e.status === 412) {
        setMessage(
          "Monitor changed concurrently. Refresh and review before retrying.",
        );
        await load();
      } else setError((e as Error).message);
    } finally {
      setSubmitting(false);
    }
  };
  const createSuppression = async () => {
    const start = Date.parse(suppression.starts_at);
    const end = Date.parse(suppression.ends_at);
    if (
      !Number.isFinite(start) ||
      !Number.isFinite(end) ||
      end <= start ||
      end - start > 31 * 86400000
    ) {
      setError(
        "Suppression must have valid offset timestamps and a positive duration of at most 31 days.",
      );
      return;
    }
    if (
      !suppression.reason.trim() ||
      !suppression.approval_reference.trim() ||
      submitting ||
      !confirm("Create this suppression?")
    )
      return;
    setSubmitting(true);
    setError("");
    try {
      const result = await qualityApi.mutate<Record<string, unknown>>(
        tenant,
        environment,
        `/monitors/${encodeURIComponent(monitorId)}/suppressions`,
        suppression,
      );
      setMessage(`Suppression created: ${JSON.stringify(result.data)}`);
      setSuppression({
        starts_at: "",
        ends_at: "",
        reason: "",
        approval_reference: "",
      });
      await refreshSection("suppressions");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSubmitting(false);
    }
  };
  if (error && !monitor)
    return <p role="alert">Monitor unavailable: {error}</p>;
  if (!monitor) return <p role="status">Loading Monitor 360…</p>;
  return (
    <section className="quality-page">
      <nav aria-label="Breadcrumb">
        <Link to="/quality">Quality</Link> /{" "}
        <Link to="/quality/monitors">Monitors</Link> / {monitor.name}
      </nav>
      <div className="quality-heading">
        <div>
          <h1>{monitor.name}</h1>
          <p>{monitor.description || "No description supplied."}</p>
        </div>
        <span className={`state state-${monitor.state}`}>{monitor.state}</span>
      </div>
      <p>Revision {monitor.revision} · concurrency token retained</p>
      {message && <p role="status">{message}</p>}
      {error && <p role="alert">Partial evidence: {error}</p>}
      <div className="quality-actions" aria-label="Monitor operations">
        <button
          disabled={!["draft", "disabled"].includes(monitor.state)}
          onClick={() => action("enable")}
        >
          Enable
        </button>
        <button
          disabled={!["enabled", "active", "learning"].includes(monitor.state)}
          onClick={() => action("disable")}
        >
          Disable
        </button>
        <button
          disabled={!["enabled", "active", "learning"].includes(monitor.state)}
          onClick={() => action("run")}
        >
          Run now
        </button>
        <button
          disabled={monitor.state === "archived"}
          onClick={() => action("archive")}
        >
          Archive
        </button>
      </div>
      <div className="tabs" role="tablist" aria-label="Monitor evidence">
        {sections.map((x) => (
          <button
            role="tab"
            aria-selected={tab === x}
            aria-controls="monitor-panel"
            onClick={() => setTab(x)}
            key={x}
          >
            {x.replace("history", "definition history")}
          </button>
        ))}
      </div>
      <div id="monitor-panel" role="tabpanel" tabIndex={0}>
        {tab === "overview" && <Overview monitor={monitor} />}{" "}
        {tab === "configuration" && (
          <pre className="review-json">{JSON.stringify(monitor, null, 2)}</pre>
        )}
        {tab === "runtime" && (
          <p>
            Runtime state is represented by the current lifecycle state (
            {monitor.state}); execution evidence is unavailable unless returned
            by the runtime provider.
          </p>
        )}
        {tab === "baselines" && monitor.state !== "archived" && (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void resetBaseline();
            }}
          >
            <h2>Reset baseline</h2>
            <label>
              Reason{" "}
              <textarea
                required
                maxLength={500}
                value={resetReason}
                onChange={(e) => setResetReason(e.target.value)}
              />
            </label>
            <button disabled={submitting || !resetReason.trim()}>
              Reset baseline
            </button>
          </form>
        )}
        {tab === "suppressions" && monitor.state !== "archived" && (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void createSuppression();
            }}
          >
            <h2>Create suppression</h2>
            <label>
              Start time with offset{" "}
              <input
                required
                placeholder="2026-08-01T10:00:00+00:00"
                value={suppression.starts_at}
                onChange={(e) =>
                  setSuppression({ ...suppression, starts_at: e.target.value })
                }
              />
            </label>
            <label>
              End time with offset{" "}
              <input
                required
                placeholder="2026-08-02T10:00:00+00:00"
                value={suppression.ends_at}
                onChange={(e) =>
                  setSuppression({ ...suppression, ends_at: e.target.value })
                }
              />
            </label>
            <label>
              Reason{" "}
              <textarea
                required
                maxLength={500}
                value={suppression.reason}
                onChange={(e) =>
                  setSuppression({ ...suppression, reason: e.target.value })
                }
              />
            </label>
            <label>
              Approval reference{" "}
              <input
                required
                maxLength={200}
                value={suppression.approval_reference}
                onChange={(e) =>
                  setSuppression({
                    ...suppression,
                    approval_reference: e.target.value,
                  })
                }
              />
            </label>
            <button disabled={submitting}>Create suppression</button>
          </form>
        )}
        {!["overview", "configuration", "runtime"].includes(tab) && (
          <EvidenceTable section={tab} items={items} />
        )}
      </div>
    </section>
  );
}
function Overview({ monitor }: { monitor: MonitorDefinition }) {
  return (
    <dl className="stream-facts">
      <div>
        <dt>Type and target</dt>
        <dd>
          {monitor.monitor_type} ·{" "}
          {shown(monitor.target.asset_id ?? monitor.target.table_name)}
        </dd>
      </div>
      <div>
        <dt>Schedule</dt>
        <dd>
          {monitor.schedule.interval} · {monitor.schedule.timezone}
        </dd>
      </div>
      <div>
        <dt>Threshold</dt>
        <dd>
          {monitor.threshold.mode}: {shown(monitor.threshold.minimum)} –{" "}
          {shown(monitor.threshold.maximum)}
        </dd>
      </div>
      <div>
        <dt>Baseline</dt>
        <dd>{shown(monitor.baseline?.method)}</dd>
      </div>
      <div>
        <dt>Latest evidence</dt>
        <dd>Open Observations and Evaluations; absence is not zero.</dd>
      </div>
    </dl>
  );
}
function EvidenceTable({
  section,
  items,
}: {
  section: string;
  items: unknown[];
}) {
  if (!items.length)
    return (
      <p>
        No {section} evidence is available. This does not mean a measured zero.
      </p>
    );
  return (
    <div className="table-scroll">
      <table>
        <caption>{section} evidence</caption>
        <thead>
          <tr>
            <th>Identity / timestamp</th>
            <th>Evidence</th>
            <th>Status / links</th>
          </tr>
        </thead>
        <tbody>
          {items.map((raw, index) => {
            const x = raw as Partial<
              Observation & Evaluation & Finding & Suppression
            > &
              Record<string, unknown>;
            const id =
              x.evaluation_id ??
              x.finding_id ??
              x.execution_id ??
              x.id ??
              index;
            return (
              <tr key={String(id)}>
                <th>
                  {shown(id)}
                  <small>
                    {shown(x.observed_at ?? x.evaluated_at ?? x.starts_at)}
                  </small>
                </th>
                <td>{"value" in x ? shown(x.value) : JSON.stringify(raw)}</td>
                <td>
                  {x.incident_id ? (
                    <Link
                      to={`/incidents/${encodeURIComponent(String(x.incident_id))}`}
                    >
                      Incident {String(x.incident_id)}
                    </Link>
                  ) : (
                    shown(x.state)
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
