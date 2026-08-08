export const allowedActivityTelemetry = [
  "event",
  "tab",
  "provider_category",
  "provider_outcome",
  "item_count_bucket",
  "unseen_count_bucket",
  "attention_count_bucket",
  "activity_type",
  "capability_id",
  "action",
  "duration_bucket",
] as const;
export function countBucket(value: number) {
  return value === 0
    ? "0"
    : value === 1
      ? "1"
      : value <= 5
        ? "2-5"
        : value <= 10
          ? "6-10"
          : value <= 25
            ? "11-25"
            : value <= 50
              ? "26-50"
              : "50+";
}
export function safeActivityTelemetry(input: Record<string, unknown>) {
  return Object.fromEntries(
    Object.entries(input).filter(([key]) =>
      (allowedActivityTelemetry as readonly string[]).includes(key),
    ),
  );
}
