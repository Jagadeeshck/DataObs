import type { ReactNode } from "react";
import type { EvidenceEnvelope } from "../../../api/quality";

export const display = (value: unknown, suffix = "") =>
  value === null || value === undefined || value === ""
    ? "Unknown"
    : `${String(value)}${suffix}`;
export function QualityMetricCard({
  label,
  value,
  detail,
}: {
  label: string;
  value: ReactNode;
  detail?: string;
}) {
  return (
    <article className="metric-card">
      <h3>{label}</h3>
      <strong>{value}</strong>
      {detail && <small>{detail}</small>}
    </article>
  );
}
export function StatusBadge({ value }: { value: string | null | undefined }) {
  return (
    <span className={`status-badge status-${value ?? "unknown"}`}>
      {value ?? "unknown"}
    </span>
  );
}
export function QualityStatusBanner({
  evidence,
}: {
  evidence: Partial<EvidenceEnvelope>;
}) {
  if (evidence.data_status === "complete" && !evidence.warnings?.length)
    return null;
  return (
    <aside className="quality-banner" role="status">
      <strong>Evidence: {evidence.data_status ?? "unknown"}</strong>
      {evidence.warnings?.map((w) => (
        <p key={w}>{w}</p>
      ))}
    </aside>
  );
}
export function MissingEvidencePanel({
  evidence,
}: {
  evidence: Partial<EvidenceEnvelope>;
}) {
  return (
    <section aria-labelledby="missing-evidence">
      <h2 id="missing-evidence">Missing evidence</h2>
      {evidence.missing_inputs?.length ? (
        <ul>
          {evidence.missing_inputs.map((x) => (
            <li key={x}>{x}</li>
          ))}
        </ul>
      ) : (
        <p>No missing inputs were reported.</p>
      )}
      <p>
        Source coverage: {evidence.source_coverage?.join(", ") || "Unknown"}
      </p>
    </section>
  );
}
export function EvidencePanel({
  evidence,
}: {
  evidence: Partial<EvidenceEnvelope>;
}) {
  return (
    <dl className="detail-grid">
      <dt>Data status</dt>
      <dd>{display(evidence.data_status)}</dd>
      <dt>Observed</dt>
      <dd>{display(evidence.observed_at)}</dd>
      <dt>Confidence</dt>
      <dd>{display(evidence.confidence)}</dd>
      <dt>Request ID</dt>
      <dd>{display(evidence.request_id)}</dd>
      <dt>Source coverage</dt>
      <dd>{evidence.source_coverage?.join(", ") || "Unknown"}</dd>
      <dt>Warnings</dt>
      <dd>{evidence.warnings?.join(", ") || "None reported"}</dd>
      <dt>Missing inputs</dt>
      <dd>{evidence.missing_inputs?.join(", ") || "None reported"}</dd>
    </dl>
  );
}
