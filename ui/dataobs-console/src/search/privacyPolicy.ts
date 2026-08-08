export const searchPrivacyPolicy = {
  version: 1,
  prohibited: [
    "query_text",
    "query_tokens",
    "result_id",
    "result_label",
    "secondary_label",
    "result_url",
    "tenant_id",
    "user_id",
    "raw_error",
  ],
  allowed: [
    "event",
    "query_length_bucket",
    "provider_id",
    "provider_status",
    "result_count_bucket",
    "duration_bucket",
    "entity_type",
    "input_method",
  ],
} as const;
export const queryLengthBucket = (length: number) =>
  length < 3 ? "0-2" : length < 8 ? "3-7" : length < 16 ? "8-15" : "16+";
export function safeSearchTelemetry(values: Record<string, unknown>) {
  return Object.fromEntries(
    Object.entries(values).filter(([key]) =>
      (searchPrivacyPolicy.allowed as readonly string[]).includes(key),
    ),
  );
}
