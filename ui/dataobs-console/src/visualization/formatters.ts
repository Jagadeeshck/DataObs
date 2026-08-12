import type { MetricUnit } from "./types";
const number = new Intl.NumberFormat("en-US", { maximumFractionDigits: 1 });
export function formatMetric(
  value: number | null | undefined,
  unit: MetricUnit,
): string {
  if (value == null || !Number.isFinite(value)) return "Unknown";
  if (unit === "percent") return `${number.format(value)}%`;
  if (unit === "bytes") {
    const a = Math.abs(value);
    if (a >= 1073741824) return `${number.format(value / 1073741824)} GiB`;
    if (a >= 1048576) return `${number.format(value / 1048576)} MiB`;
    return `${number.format(value)} bytes`;
  }
  if (unit === "ms") return `${number.format(value)} ms`;
  if (unit === "seconds") return `${number.format(value)} seconds`;
  if (unit === "score") return number.format(value);
  return `${number.format(value)}${unit === "count" ? "" : ` ${unit}`}`;
}
export function formatTimestamp(value: number): string {
  return new Intl.DateTimeFormat("en-GB", {
    dateStyle: "medium",
    timeStyle: "medium",
    timeZone: "UTC",
  }).format(value);
}
export function formatObserved(value: number | null, unit: MetricUnit): string {
  return value === null ? "No observation" : formatMetric(value, unit);
}
