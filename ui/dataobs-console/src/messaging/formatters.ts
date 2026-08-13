import type { MetricEvidenceState } from "./types";

export function formatMetric(
  value: number | null | undefined,
  state: MetricEvidenceState,
  unit = "",
): string {
  if (state === "unsupported") return "Not applicable";
  if (state === "unavailable") return "Unavailable";
  if (value === null || value === undefined || state === "missing")
    return "No observation";
  return `${value.toLocaleString()}${unit ? ` ${unit}` : ""}`;
}

export const formatCoverage = (value: number) =>
  `${Math.round(Math.max(0, Math.min(1, value)) * 100)}%`;
