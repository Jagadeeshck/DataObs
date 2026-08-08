import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  incidentsApi,
  type IncidentDetail as Detail,
  type TimelineEvent,
} from "../../api/incidents";
import { useProductContext } from "../../state/context";

export function IncidentDetail() {
  const { incidentId = "" } = useParams();
  const { tenant, environment } = useProductContext();
  const [item, setItem] = useState<Detail>();
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [status, setStatus] = useState("Loading incident…");
  const [comment, setComment] = useState("");
  const [preview, setPreview] = useState<Record<string, unknown>>();
  const [mutation, setMutation] = useState<{
    fingerprint: string;
    key: string;
  }>();
  const [submitting, setSubmitting] = useState(false);
  const load = () => {
    setStatus("Loading incident…");
    Promise.all([
      incidentsApi.detail(tenant, environment, incidentId),
      incidentsApi.timeline(tenant, environment, incidentId),
    ])
      .then(([detail, timeline]) => {
        setItem(detail);
        setEvents(timeline.items);
        setStatus("");
      })
      .catch(() =>
        setStatus("Incident data is unavailable or permission was denied."),
      );
  };
  useEffect(() => {
    Promise.all([
      incidentsApi.detail(tenant, environment, incidentId),
      incidentsApi.timeline(tenant, environment, incidentId),
    ])
      .then(([detail, timeline]) => {
        setItem(detail);
        setEvents(timeline.items);
        setStatus("");
      })
      .catch(() =>
        setStatus("Incident data is unavailable or permission was denied."),
      );
  }, [tenant, environment, incidentId]);
  const mutate = (body: Record<string, unknown>) => {
    if (!item || submitting) return;
    const payload = { revision: item.revision, ...body };
    const fingerprint = JSON.stringify([
      tenant,
      environment,
      incidentId,
      payload,
    ]);
    const operation =
      mutation?.fingerprint === fingerprint
        ? mutation
        : { fingerprint, key: crypto.randomUUID() };
    setMutation(operation);
    setSubmitting(true);
    return incidentsApi
      .mutate(tenant, environment, incidentId, payload, operation.key)
      .then(() => {
        setMutation(undefined);
        return load();
      })
      .catch((error: { status?: number }) => {
        setStatus(
          error.status === 409
            ? "This incident changed. Refreshed; review it before trying again."
            : "The change could not be saved.",
        );
        load();
      })
      .finally(() => setSubmitting(false));
  };
  return (
    <main className="page incident-page" aria-labelledby="incident-title">
      <p role="status" aria-live="polite">
        {status}
      </p>
      {item ? (
        <>
          <div className="eyebrow">INCIDENTS / {item.id}</div>
          <h1 id="incident-title">{item.title}</h1>
          <p>
            <strong>{item.severity}</strong> · {item.state} ·{" "}
            {item.owner || "Unassigned"}
          </p>
          <nav aria-label="Workbench sections">
            <a href="#overview">Overview</a> · <a href="#findings">Findings</a>{" "}
            · <a href="#evidence">Evidence</a> ·{" "}
            <a href="#assets">Affected Assets</a> ·{" "}
            <a href="#timeline">Timeline</a> ·{" "}
            <a href="#collaboration">Collaboration</a> ·{" "}
            <a href="#actions">Automation</a>
          </nav>
          <section id="overview" className="panel">
            <h2>Overview</h2>
            <p>{item.impact_summary || "Impact is unknown."}</p>
            <h3>Severity factors</h3>
            <pre>{JSON.stringify(item.severity_factors, null, 2)}</pre>
            <p>
              Occurrences: {item.occurrence_count}. Evidence coverage:{" "}
              {item.evidence_coverage}.
            </p>
            {item.warnings.map((w) => (
              <p key={w}>{w}</p>
            ))}
            <button
              disabled={submitting}
              onClick={() => mutate({ state: "acknowledged" })}
            >
              Acknowledge
            </button>
          </section>
          <section id="findings" className="panel">
            <h2>Findings</h2>
            <ul>
              {item.finding_references.map((id) => (
                <li key={id}>{id}</li>
              ))}
            </ul>
          </section>
          <section id="evidence" className="panel">
            <h2>Latest safe evidence</h2>
            {item.latest_evidence.length ? (
              <pre>{JSON.stringify(item.latest_evidence, null, 2)}</pre>
            ) : (
              <p>Evidence is unknown; no value has been measured.</p>
            )}
          </section>
          <section id="assets" className="panel">
            <h2>Affected Assets</h2>
            <ul>
              {item.affected_assets.map((asset) => (
                <li key={asset}>{asset}</li>
              ))}
            </ul>
          </section>
          <section id="timeline" className="panel">
            <h2>Timeline</h2>
            <ol>
              {events.map((event) => (
                <li key={event.event_id}>
                  <time dateTime={event.timestamp}>
                    {new Date(event.timestamp).toLocaleString()}
                  </time>{" "}
                  — {event.summary} ({event.actor})
                </li>
              ))}
            </ol>
          </section>
          <section id="collaboration" className="panel">
            <h2>Collaboration</h2>
            <label>
              Add comment{" "}
              <textarea
                value={comment}
                onChange={(e) => setComment(e.target.value)}
              />
            </label>
            <button
              disabled={!comment.trim() || submitting}
              onClick={() => {
                mutate({ comment });
                setComment("");
              }}
            >
              Add comment
            </button>
          </section>
          <section id="actions" className="panel">
            <h2>Automation</h2>
            <p>
              Actions are previewed only. Provider acceptance is not proof of
              recovery, and automation never resolves this incident.
            </p>
            <button
              disabled={!item.affected_assets[0]}
              aria-describedby="automation-disabled-reason"
              onClick={() =>
                incidentsApi
                  .preview(
                    tenant,
                    environment,
                    incidentId,
                    "rerun_scan",
                    item.revision,
                    item.affected_assets[0],
                  )
                  .then(setPreview)
              }
            >
              Preview rerun scan
            </button>
            <p id="automation-disabled-reason">
              {!item.affected_assets[0]
                ? "A target is required before preview is available."
                : "Preview has no side effects."}
            </p>
            {preview ? (
              <div role="status" aria-live="polite">
                <h3>Deterministic action preview</h3>
                <p>Target: {String((preview.target as { id?: string }).id)}</p>
                <p>Risk: {String(preview.risk)}</p>
                <p>Provider: {String(preview.provider_state)}</p>
                <p>Policy: {String(preview.policy_decision)}</p>
                <p>Approval required: {String(preview.approval_required)}</p>
                <p>Timeout: {String(preview.timeout_seconds)} seconds</p>
                <p>Verification: {String(preview.verification_plan)}</p>
                <p>Rollback: {String(preview.rollback_description)}</p>
                <p>{String((preview.warnings as string[])[0])}</p>
                <button disabled title="The executor is not configured.">
                  Execute unavailable
                </button>
              </div>
            ) : null}
          </section>
        </>
      ) : null}
    </main>
  );
}
