import type { ReactNode } from "react";
import type { VisualizationStateKind } from "./types";
const labels: Record<VisualizationStateKind, string> = {
  loading: "Loading visualization…",
  empty: "No observations",
  partial: "Partial results",
  stale: "Data is stale",
  unavailable: "Visualization unavailable",
  permission_denied: "Permission denied",
  not_configured: "Not configured",
  error: "Unable to render visualization",
  rate_limited: "Rate limited",
};
export function VisualizationState({
  state,
  detail,
  children,
}: {
  state?: VisualizationStateKind;
  detail?: string;
  children?: ReactNode;
}) {
  if (!state) return <>{children}</>;
  return (
    <div
      className={`viz-state viz-state--${state}`}
      role={state === "error" ? "alert" : "status"}
    >
      <strong>{labels[state]}</strong>
      {detail && <p>{detail}</p>}
    </div>
  );
}
