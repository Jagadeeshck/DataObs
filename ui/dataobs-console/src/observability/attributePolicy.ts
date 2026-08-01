import type { Attributes } from "@opentelemetry/api";

type Policy = {
  type: "string" | "number" | "boolean";
  cardinality: "low" | "bounded";
  required: boolean;
  source: string;
  redaction: "none" | "identifier";
  maximumLength: number;
  allowed?: RegExp;
};

export const attributePolicy = {
  "service.name": {
    type: "string",
    cardinality: "low",
    required: true,
    source: "runtime",
    redaction: "none",
    maximumLength: 64,
  },
  "service.version": {
    type: "string",
    cardinality: "bounded",
    required: true,
    source: "runtime",
    redaction: "none",
    maximumLength: 64,
  },
  "deployment.environment": {
    type: "string",
    cardinality: "low",
    required: true,
    source: "runtime",
    redaction: "none",
    maximumLength: 32,
  },
  "dataobs.console.route_id": {
    type: "string",
    cardinality: "low",
    required: false,
    source: "route-manifest",
    redaction: "none",
    maximumLength: 64,
    allowed: /^[a-z0-9-]+$/,
  },
  "dataobs.console.capability_id": {
    type: "string",
    cardinality: "low",
    required: false,
    source: "route-manifest",
    redaction: "none",
    maximumLength: 64,
  },
  "dataobs.console.owner_team": {
    type: "string",
    cardinality: "low",
    required: false,
    source: "route-manifest",
    redaction: "none",
    maximumLength: 16,
  },
  "dataobs.console.navigation_type": {
    type: "string",
    cardinality: "low",
    required: false,
    source: "browser",
    redaction: "none",
    maximumLength: 24,
  },
  "dataobs.console.error_category": {
    type: "string",
    cardinality: "low",
    required: false,
    source: "error-capture",
    redaction: "none",
    maximumLength: 32,
  },
  "dataobs.console.error_fingerprint": {
    type: "string",
    cardinality: "bounded",
    required: false,
    source: "error-capture",
    redaction: "identifier",
    maximumLength: 16,
  },
  "dataobs.console.request_id": {
    type: "string",
    cardinality: "bounded",
    required: false,
    source: "response-header",
    redaction: "identifier",
    maximumLength: 64,
    allowed: /^[A-Za-z0-9._:-]+$/,
  },
  "dataobs.console.recovery_action": {
    type: "string",
    cardinality: "low",
    required: false,
    source: "boundary",
    redaction: "none",
    maximumLength: 24,
  },
  "dataobs.console.chunk_name": {
    type: "string",
    cardinality: "low",
    required: false,
    source: "route-manifest",
    redaction: "none",
    maximumLength: 64,
  },
  "dataobs.console.metric_name": {
    type: "string",
    cardinality: "low",
    required: false,
    source: "performance",
    redaction: "none",
    maximumLength: 48,
  },
  "dataobs.console.metric_value": {
    type: "number",
    cardinality: "bounded",
    required: false,
    source: "performance",
    redaction: "none",
    maximumLength: 32,
  },
  "dataobs.console.metric_unit": {
    type: "string",
    cardinality: "low",
    required: false,
    source: "performance",
    redaction: "none",
    maximumLength: 12,
  },
  "http.request.method": {
    type: "string",
    cardinality: "low",
    required: false,
    source: "transport",
    redaction: "none",
    maximumLength: 12,
  },
  "http.response.status_code": {
    type: "number",
    cardinality: "low",
    required: false,
    source: "transport",
    redaction: "none",
    maximumLength: 3,
  },
  "url.template": {
    type: "string",
    cardinality: "bounded",
    required: false,
    source: "transport",
    redaction: "none",
    maximumLength: 120,
  },
  "error.type": {
    type: "string",
    cardinality: "low",
    required: false,
    source: "error-capture",
    redaction: "none",
    maximumLength: 48,
  },
} as const satisfies Record<string, Policy>;

export function safeAttributes(values: Record<string, unknown>): Attributes {
  const result: Attributes = {};
  for (const [name, value] of Object.entries(values)) {
    const policy = attributePolicy[name as keyof typeof attributePolicy];
    if (!policy) {
      if (import.meta.env.DEV || import.meta.env.MODE === "test")
        throw new Error(`Unknown telemetry attribute: ${name}`);
      continue;
    }
    if (typeof value !== policy.type) continue;
    if (typeof value === "string") {
      const bounded = value.slice(0, policy.maximumLength);
      if (
        "allowed" in policy &&
        policy.allowed &&
        !policy.allowed.test(bounded)
      )
        continue;
      result[name] = bounded;
    } else result[name] = value as number | boolean;
  }
  return result;
}
