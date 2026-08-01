import type {
  DataStatus,
  LagCell,
  MetricSample,
  Partition,
} from "../../api/client";

export const display = (
  value: string | number | null | undefined,
  fallback = "Unknown",
) =>
  value === null || value === undefined || value === ""
    ? fallback
    : String(value);
export const MetricCard = ({
  label,
  value,
  unit,
}: {
  label: string;
  value?: string | number | null;
  unit?: string;
}) => (
  <div className="metric-card">
    <span>{label}</span>
    <strong>{display(value)}</strong>
    {value != null && unit && <small>{unit}</small>}
  </div>
);
export const HealthBadge = ({ health }: { health?: string }) => (
  <span
    className={`health health-${health ?? "unknown"}`}
    aria-label={`Health: ${health ?? "unknown"}`}
  >
    {health === "healthy" ? "✓" : health === "critical" ? "!" : "●"}{" "}
    {health ?? "unknown"}
  </span>
);
export const MissingInputs = ({ inputs }: { inputs?: string[] }) =>
  inputs?.length ? (
    <p className="missing-inputs">
      <strong>Missing inputs:</strong> {inputs.join(", ")}
    </p>
  ) : null;
export const StaleIndicator = () => (
  <span className="stale-indicator">Stale</span>
);
export function DataStatusBanner({
  status,
  warnings = [],
  observedAt,
}: {
  status?: DataStatus | string;
  warnings?: string[];
  observedAt?: string;
}) {
  return (
    <div role="status" className={`data-state status-${status ?? "unknown"}`}>
      <strong>{display(status)}</strong>
      {observedAt ? ` — observed ${new Date(observedAt).toLocaleString()}` : ""}
      {warnings.length ? <span> — {warnings.join("; ")}</span> : null}
    </div>
  );
}
export const EvidenceSummary = ({
  coverage = [],
  confidence,
}: {
  coverage?: string[];
  confidence?: number | null;
}) => (
  <p>
    Source coverage: {coverage.length ? coverage.join(", ") : "Unknown"}.
    Confidence:{" "}
    {confidence == null ? "Unknown" : `${Math.round(confidence * 100)}%`}.
  </p>
);
export const EmptyState = ({
  children = "No measured evidence matches this view.",
}: {
  children?: React.ReactNode;
}) => (
  <div className="empty-state">
    <h2>No results</h2>
    <p>{children}</p>
  </div>
);
export const UnavailableState = ({ message }: { message: string }) => (
  <div role="alert" className="data-state status-unavailable">
    <strong>Unavailable</strong> — {message}
  </div>
);
export function AccessibleSparkline({
  samples = [],
  label,
  unit,
  period,
}: {
  samples?: MetricSample[];
  label: string;
  unit: string;
  period?: number;
}) {
  const measured = samples.filter((x) => x.value != null);
  if (!measured.length)
    return (
      <EmptyState>No {label.toLowerCase()} samples are available.</EmptyState>
    );
  const values = measured.map((x) => x.value as number),
    max = Math.max(...values, 1),
    min = Math.min(...values);
  const points = values
    .map(
      (v, i) =>
        `${(i / Math.max(values.length - 1, 1)) * 100},${38 - ((v - min) / Math.max(max - min, 1)) * 34}`,
    )
    .join(" ");
  return (
    <figure className="sparkline">
      <figcaption>
        <strong>{label}</strong>: latest {values.at(-1)} {unit}; {values.length}{" "}
        samples{period ? ` every ${period}s` : ""}.
      </figcaption>
      <svg
        viewBox="0 0 100 40"
        role="img"
        aria-label={`${label} trend, ${values.length} samples in ${unit}`}
      >
        <polyline
          points={points}
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
        />
      </svg>
    </figure>
  );
}
export function PartitionHealthGrid({
  partitions = [],
}: {
  partitions?: Partition[];
}) {
  return (
    <div>
      <div
        className="health-grid"
        role="grid"
        aria-label="Partition health grid"
      >
        {partitions.map((p) => (
          <button
            key={p.partition}
            role="gridcell"
            className={`health-cell health-${p.health ?? "unknown"}`}
            aria-label={`Partition ${p.partition}: ${p.health ?? "unknown"}`}
          >
            {p.partition}
            <small>{p.health ?? "?"}</small>
          </button>
        ))}
      </div>
      <div className="table-scroll" tabIndex={0}>
        <table>
          <caption>Partition health table alternative</caption>
          <thead>
            <tr>
              <th>Partition</th>
              <th>Health</th>
            </tr>
          </thead>
          <tbody>
            {partitions.map((p) => (
              <tr key={p.partition}>
                <td>{p.partition}</td>
                <td>{p.health ?? "Unknown"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
export function LagHeatmap({
  cells = [],
  truncated = false,
}: {
  cells?: LagCell[];
  truncated?: boolean;
}) {
  return (
    <div>
      {truncated && (
        <p role="status">Partition view truncated to the bounded result.</p>
      )}
      <div
        className="health-grid lag-grid"
        role="grid"
        aria-label="Consumer lag heatmap"
      >
        {cells.map((c) => (
          <button
            key={`${c.topic}-${c.partition}`}
            role="gridcell"
            className={`health-cell lag-${c.lag == null ? "unknown" : c.lag === 0 ? "zero" : "present"}`}
            aria-label={`${c.topic} partition ${c.partition}: lag ${display(c.lag)}${c.stale ? ", stale" : ""}`}
          >
            {c.partition}
            <small>
              {c.lag == null ? "?" : c.lag}
              {c.stale ? " stale" : ""}
            </small>
          </button>
        ))}
      </div>
      <div className="table-scroll" tabIndex={0}>
        <table>
          <caption>Lag heatmap table alternative</caption>
          <thead>
            <tr>
              <th>Topic</th>
              <th>Partition</th>
              <th>Lag</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {cells.map((c) => (
              <tr key={`${c.topic}-${c.partition}`}>
                <td>{c.topic}</td>
                <td>{c.partition}</td>
                <td>{display(c.lag)}</td>
                <td>{c.stale ? "Stale" : (c.data_status ?? "Unknown")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
