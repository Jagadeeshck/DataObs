import type { ReactNode } from "react";
export type EvidenceState =
  | "healthy"
  | "warning"
  | "critical"
  | "unknown"
  | "not_configured"
  | "unavailable"
  | "stale"
  | "partial";
export function HealthBadge({ state }: { state: EvidenceState }) {
  return (
    <span
      className={`health ${state}`}
      aria-label={`Evidence state: ${state.replace("_", " ")}`}
    >
      ● {state.replace("_", " ")}
    </span>
  );
}
export function MetricCard({
  label,
  value,
}: {
  label: string;
  value: ReactNode | null | undefined;
}) {
  return (
    <div className="metric-card">
      <strong>{value ?? "Unknown"}</strong>
      <span>{label}</span>
    </div>
  );
}
export function DataStatusBanner({
  state,
  children,
  requestId,
}: {
  state: EvidenceState;
  children: ReactNode;
  requestId?: string;
}) {
  return (
    <div
      className={`data-status ${state}`}
      role={state === "critical" ? "alert" : "status"}
    >
      <HealthBadge state={state} /> <span>{children}</span>
      {requestId && <small>Request ID: {requestId}</small>}
    </div>
  );
}
export function LoadingSkeleton({
  label = "Loading evidence…",
}: {
  label?: string;
}) {
  return (
    <div className="loading-skeleton" role="status">
      {label}
    </div>
  );
}
export function ErrorState({
  message,
  retry,
  requestId,
}: {
  message: string;
  retry?: () => void;
  requestId?: string;
}) {
  return (
    <DataStatusBanner state="unavailable" requestId={requestId}>
      {message} {retry && <button onClick={retry}>Retry</button>}
    </DataStatusBanner>
  );
}
export function EmptyState({
  title,
  children,
}: {
  title: string;
  children?: ReactNode;
}) {
  return (
    <section className="empty-state">
      <h2>{title}</h2>
      {children}
    </section>
  );
}
