export function boundedLabel(value: string, max = 120): string {
  return value
    .replace(/[\r\n\t]/g, " ")
    .trim()
    .slice(0, max);
}
export function trendSummary(values: readonly (number | null)[]): string {
  const observed = values.filter((v): v is number => v !== null);
  if (observed.length < 2)
    return observed.length
      ? "One observation; trend unavailable"
      : "No observations";
  const delta = observed.at(-1)! - observed[0];
  return delta === 0
    ? "Trend is flat"
    : `Trend is ${delta > 0 ? "increasing" : "decreasing"}`;
}
