import { Link, useParams, useSearchParams } from "react-router-dom";
import * as q from "../../api/quality";
import { useProductContext } from "../../state/context";
import {
  display,
  EvidencePanel,
  QualityStatusBanner,
  StatusBadge,
} from "./components/QualityComponents";
import { useQualityRequest } from "./useQualityRequest";
const tabs = [
  "overview",
  "observations",
  "evaluations",
  "baselines",
  "findings",
  "incidents",
  "suppressions",
  "history",
  "evidence",
] as const;
export function Monitor360() {
  const { monitorId = "" } = useParams();
  const { tenant, environment } = useProductContext();
  const [params, setParams] = useSearchParams();
  const tab = tabs.includes(params.get("tab") as never)
    ? params.get("tab")!
    : "overview";
  const monitor = useQualityRequest(
    (s) => q.qualityMonitor(tenant, environment, monitorId, s),
    [tenant, environment, monitorId],
  );
  const observations = useQualityRequest(
    (s) =>
      q.qualityMonitorObservations(
        tenant,
        environment,
        monitorId,
        undefined,
        s,
      ),
    [tenant, environment, monitorId],
  );
  const evaluations = useQualityRequest(
    (s) =>
      q.qualityMonitorEvaluations(tenant, environment, monitorId, undefined, s),
    [tenant, environment, monitorId],
  );
  const baselines = useQualityRequest(
    (s) =>
      q.qualityMonitorBaselines(tenant, environment, monitorId, undefined, s),
    [tenant, environment, monitorId],
  );
  const findings = useQualityRequest(
    (s) =>
      q.qualityMonitorFindings(tenant, environment, monitorId, undefined, s),
    [tenant, environment, monitorId],
  );
  const incidents = useQualityRequest(
    (s) =>
      q.qualityMonitorIncidents(tenant, environment, monitorId, undefined, s),
    [tenant, environment, monitorId],
  );
  const suppressions = useQualityRequest(
    (s) =>
      q.qualityMonitorSuppressions(
        tenant,
        environment,
        monitorId,
        undefined,
        s,
      ),
    [tenant, environment, monitorId],
  );
  const history = useQualityRequest(
    (s) =>
      q.qualityMonitorHistory(tenant, environment, monitorId, undefined, s),
    [tenant, environment, monitorId],
  );
  if (monitor.loading)
    return <p role="status">Loading monitor investigation…</p>;
  if (monitor.error) return <p role="alert">{monitor.error}</p>;
  const m = monitor.data;
  if (!m) return null;
  const select = (v: string) => {
    const n = new URLSearchParams(params);
    if (v === "overview") n.delete("tab");
    else n.set("tab", v);
    setParams(n);
  };
  return (
    <section>
      <header>
        <p>
          <Link to="/quality?tab=monitors">← Monitor inventory</Link>
        </p>
        <h1>{m.name}</h1>
        <p>Monitor 360 · read-only investigation</p>
      </header>
      <QualityStatusBanner evidence={m} />
      <nav className="tabs" aria-label="Monitor evidence sections">
        {tabs.map((x) => (
          <button
            key={x}
            aria-current={x === tab ? "page" : undefined}
            onClick={() => select(x)}
          >
            {x[0].toUpperCase() + x.slice(1)}
          </button>
        ))}
      </nav>
      {tab === "overview" && <Overview m={m} />}{" "}
      {tab === "observations" && <Observations data={observations.data} />}{" "}
      {tab === "evaluations" && <Evaluations data={evaluations.data} />}{" "}
      {tab === "baselines" && <Baselines data={baselines.data} />}{" "}
      {tab === "findings" && <Findings data={findings.data} />}{" "}
      {tab === "incidents" && <Incidents data={incidents.data} />}{" "}
      {tab === "suppressions" && <Suppressions data={suppressions.data} />}{" "}
      {tab === "history" && <History data={history.data} />}{" "}
      {tab === "evidence" && <EvidencePanel evidence={m} />}
    </section>
  );
}
function Overview({ m }: { m: q.QualityMonitor }) {
  const safeTarget = [
    "asset_id",
    "field_id",
    "pathway_id",
    "pipeline_id",
    "service_id",
    "source_type",
    "schema_name",
    "table_name",
    "columns",
    "timestamp_column",
  ].filter((k) => m.target[k] !== undefined);
  return (
    <>
      <h2>Overview</h2>
      <dl className="detail-grid">
        <dt>Monitor ID</dt>
        <dd>{m.id}</dd>
        <dt>Type</dt>
        <dd>{m.monitor_type}</dd>
        <dt>State</dt>
        <dd>
          <StatusBadge value={m.state} />
        </dd>
        <dt>Target</dt>
        <dd>{m.target_display_name}</dd>
        <dt>Managed by</dt>
        <dd>{m.managed_by}</dd>
        <dt>Creation source</dt>
        <dd>{m.creation_source}</dd>
        <dt>Schedule</dt>
        <dd>{m.schedule_interval}</dd>
        <dt>Threshold mode</dt>
        <dd>{m.threshold_mode}</dd>
        <dt>Threshold range</dt>
        <dd>
          {display(m.threshold?.minimum)} – {display(m.threshold?.maximum)}
        </dd>
        <dt>Baseline method</dt>
        <dd>{display(m.baseline?.method)}</dd>
        <dt>Sensitivity</dt>
        <dd>{display(m.baseline?.sensitivity)}</dd>
        <dt>Severity</dt>
        <dd>{m.severity}</dd>
        <dt>Consecutive breaches</dt>
        <dd>{display(m.alert?.consecutive_breaches)}</dd>
        <dt>Revision / version</dt>
        <dd>
          {m.revision} / {m.monitor_version}
        </dd>
        <dt>Last observation</dt>
        <dd>{display(m.last_observation_at)}</dd>
        <dt>Last evaluation</dt>
        <dd>{display(m.last_evaluation_at)}</dd>
        <dt>Open findings</dt>
        <dd>{display(m.open_finding_count)}</dd>
        <dt>Highest severity</dt>
        <dd>{display(m.highest_open_severity)}</dd>
        <dt>Incidents</dt>
        <dd>{display(m.incident_count)}</dd>
        <dt>Active suppressions</dt>
        <dd>{display(m.active_suppression_count)}</dd>
        <dt>Cold-start state</dt>
        <dd>{display(m.cold_start_state)}</dd>
        <dt>Health</dt>
        <dd>{m.health}</dd>
        <dt>Staleness</dt>
        <dd>{m.stale === null ? "Unknown" : m.stale ? "Stale" : "Current"}</dd>
      </dl>
      <h3>Allowlisted target summary</h3>
      <dl className="detail-grid">
        {safeTarget.map((k) => (
          <span key={k}>
            <dt>{k.replaceAll("_", " ")}</dt>
            <dd>
              {display(
                Array.isArray(m.target[k])
                  ? (m.target[k] as unknown[]).join(", ")
                  : m.target[k],
              )}
            </dd>
          </span>
        ))}
      </dl>
    </>
  );
}
function Table({
  caption,
  headers,
  rows,
}: {
  caption: string;
  headers: string[];
  rows: (string | number)[][];
}) {
  return (
    <div className="table-scroll">
      <table>
        <caption>{caption}</caption>
        <thead>
          <tr>
            {headers.map((x) => (
              <th key={x}>{x}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              {r.map((x, j) =>
                j === 0 ? <th key={j}>{x}</th> : <td key={j}>{x}</td>,
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
function Observations({
  data,
}: {
  data?: q.QualityPage<q.QualityObservation>;
}) {
  const rows =
    data?.items.map((x) => [
      display(x.observed_at),
      display(x.value),
      x.unit,
      display(x.sample_count),
      x.missing_data ? "Missing" : "Measured",
      x.provider,
      display(x.collection_duration_ms, " ms"),
      x.definition_revision,
      display(x.trace_id),
    ]) ?? [];
  return (
    <section>
      <h2>Observations</h2>
      <p role="img" aria-label="Observation trend text summary">
        Trend contains {rows.length} measured observation points. Values marked
        Unknown are not zero.
      </p>
      <Table
        caption="Observation trend table alternative"
        headers={[
          "Observed time",
          "Value",
          "Unit",
          "Sample count",
          "Missing data",
          "Provider",
          "Collection duration",
          "Definition revision",
          "Trace ID",
        ]}
        rows={rows}
      />
    </section>
  );
}
function Evaluations({ data }: { data?: q.QualityPage<q.QualityEvaluation> }) {
  return (
    <section>
      <h2>Evaluations</h2>
      <Table
        caption="Monitor evaluations"
        headers={[
          "Evaluated",
          "Actual",
          "Expected min",
          "Expected max",
          "Method",
          "Baseline",
          "Anomaly",
          "Breached",
          "Confidence",
          "Cold start",
          "Missing inputs",
          "Exclusions",
        ]}
        rows={
          data?.items.map((x) => [
            display(x.evaluated_at),
            display(x.actual_value),
            display(x.expected_minimum),
            display(x.expected_maximum),
            x.method,
            display(x.baseline_version),
            display(x.anomaly_score),
            x.missing_inputs.length
              ? "Indeterminate (inputs missing)"
              : x.breached
                ? "Breached"
                : "Not breached",
            display(x.confidence),
            x.cold_start_state,
            x.missing_inputs.join(", ") || "None",
            x.exclusion_reasons.join(", ") || "None",
          ]) ?? []
        }
      />
    </section>
  );
}
function Baselines({ data }: { data?: q.QualityPage<q.QualityBaseline> }) {
  return (
    <section>
      <h2>Baseline version history</h2>
      <Table
        caption="Baseline versions"
        headers={[
          "Version",
          "Method",
          "Expected range",
          "Samples",
          "Sensitivity",
          "Seasonality",
          "Cold start",
          "Created",
          "Active",
        ]}
        rows={
          data?.items.map((x) => [
            x.baseline_version,
            x.method,
            `${display(x.expected_minimum)} – ${display(x.expected_maximum)}`,
            display(x.sample_count),
            display(x.sensitivity),
            x.seasonality.join(", "),
            display(x.cold_start_state),
            display(x.created_at),
            display(x.active),
          ]) ?? []
        }
      />
    </section>
  );
}
function Findings({ data }: { data?: q.QualityPage<q.QualityFinding> }) {
  return (
    <section>
      <h2>Findings</h2>
      <Table
        caption="Monitor findings"
        headers={[
          "Finding",
          "State",
          "Severity",
          "Evaluation",
          "Incident",
          "Relationship",
        ]}
        rows={
          data?.items.map((x) => [
            x.finding_id,
            x.state,
            x.severity,
            x.evaluation_id,
            display(x.incident_id),
            x.relationship,
          ]) ?? []
        }
      />
    </section>
  );
}
function Incidents({
  data,
}: {
  data?: q.QualityPage<q.QualityIncidentRelationship>;
}) {
  return (
    <section>
      <h2>Incident relationships</h2>
      <p>
        Relationships describe linkage evidence and do not assert root cause.
      </p>
      <Table
        caption="Incident relationships"
        headers={[
          "Incident",
          "Relationship",
          "Finding",
          "State",
          "Severity",
          "Observed",
        ]}
        rows={
          data?.items.map((x) => [
            x.incident_id,
            x.relationship,
            x.finding_id,
            display(x.state),
            display(x.severity),
            display(x.observed_at),
          ]) ?? []
        }
      />
    </section>
  );
}
function Suppressions({
  data,
}: {
  data?: q.QualityPage<q.QualitySuppression>;
}) {
  return (
    <section>
      <h2>Suppressions</h2>
      <p>Current and recent suppressions are read-only.</p>
      <Table
        caption="Monitor suppressions"
        headers={["ID", "Starts", "Ends", "Reason", "Approved by", "State"]}
        rows={
          data?.items.map((x) => [
            x.id,
            x.starts_at,
            x.ends_at,
            x.reason,
            x.approved_by,
            x.state,
          ]) ?? []
        }
      />
    </section>
  );
}
function History({
  data,
}: {
  data?: q.QualityPage<q.QualityDefinitionHistory>;
}) {
  return (
    <section>
      <h2>Definition history</h2>
      <Table
        caption="Safe definition revisions"
        headers={[
          "Revision",
          "Action",
          "Actor",
          "ETag",
          "Checksum",
          "Occurred",
        ]}
        rows={
          data?.items.map((x) => [
            x.revision,
            x.action,
            x.actor,
            x.etag,
            x.definition_checksum,
            display(x.occurred_at),
          ]) ?? []
        }
      />
    </section>
  );
}
