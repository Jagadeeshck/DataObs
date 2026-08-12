import type { MetricUnit } from "./types";
import { formatMetric } from "./formatters";
export function RankedList({
  items,
  unit,
  label,
}: {
  items: readonly { id: string; label: string; value: number | null }[];
  unit: MetricUnit;
  label: string;
}) {
  return (
    <ol className="viz-ranked" aria-label={label}>
      {items.map((x) => (
        <li key={x.id}>
          <span>{x.label}</span>
          <strong>{formatMetric(x.value, unit)}</strong>
        </li>
      ))}
    </ol>
  );
}
