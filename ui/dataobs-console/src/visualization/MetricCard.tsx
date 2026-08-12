import type { MetricUnit, EvidenceAvailability, EvidenceKind } from "./types";
import { formatMetric } from "./formatters";
import { availabilityLabels, evidenceLabels } from "./semantics";
export function MetricCard({
  label,
  value,
  unit,
  kind = "measured",
  availability = "available",
  detail,
}: {
  label: string;
  value: number | null;
  unit: MetricUnit;
  kind?: EvidenceKind;
  availability?: EvidenceAvailability;
  detail?: string;
}) {
  return (
    <article className="viz-metric-card">
      <span>{label}</span>
      <strong>{formatMetric(value, unit)}</strong>
      <small>
        {evidenceLabels[kind]} · {availabilityLabels[availability]}
      </small>
      {detail && <p>{detail}</p>}
    </article>
  );
}
