export interface BrowserObservabilityConfig {
  enabled: boolean;
  serviceName: string;
  serviceVersion: string;
  deploymentEnvironment: string;
  otlpHttpEndpoint: string;
  traceSampleRatio: number;
  captureWebVitals: boolean;
  captureLongTasks: boolean;
  captureResourceSummary: boolean;
  propagateTraceHeaders: boolean;
  tracePropagationAllowlist: string[];
  diagnosticsEnabled: boolean;
  debug: boolean;
  exportIntervalMs: number;
  maxQueuedSpans: number;
  maxQueuedMetrics: number;
}

export type RuntimeConsoleConfig = {
  apiBaseUrl?: string;
  observability?: Partial<BrowserObservabilityConfig>;
};

declare global {
  interface Window {
    __DATAOBS_CONFIG__?: RuntimeConsoleConfig;
  }
}

export const disabledObservabilityConfig: BrowserObservabilityConfig = {
  enabled: false,
  serviceName: "dataobs-console",
  serviceVersion: "unknown",
  deploymentEnvironment: "unknown",
  otlpHttpEndpoint: "",
  traceSampleRatio: 0.1,
  captureWebVitals: true,
  captureLongTasks: true,
  captureResourceSummary: false,
  propagateTraceHeaders: false,
  tracePropagationAllowlist: [],
  diagnosticsEnabled: false,
  debug: false,
  exportIntervalMs: 5000,
  maxQueuedSpans: 256,
  maxQueuedMetrics: 128,
};

export type ConfigResult = {
  config: BrowserObservabilityConfig;
  valid: boolean;
  issues: string[];
};

const boundedInteger = (value: unknown, minimum: number, maximum: number) =>
  Number.isInteger(value) &&
  Number(value) >= minimum &&
  Number(value) <= maximum;

export function parseObservabilityConfig(
  raw: unknown,
  pageUrl = location.href,
): ConfigResult {
  if (!raw || typeof raw !== "object")
    return { config: disabledObservabilityConfig, valid: true, issues: [] };
  const input = raw as Record<string, unknown>;
  if (input.enabled !== true)
    return {
      config: { ...disabledObservabilityConfig },
      valid: true,
      issues: [],
    };
  const issues: string[] = [];
  let endpoint: URL | undefined;
  try {
    endpoint = new URL(String(input.otlpHttpEndpoint ?? ""), pageUrl);
    if (
      endpoint.username ||
      endpoint.password ||
      endpoint.search ||
      endpoint.hash
    )
      issues.push(
        "export endpoint must not contain credentials, query, or fragment",
      );
    const page = new URL(pageUrl);
    const local = ["localhost", "127.0.0.1", "[::1]"].includes(page.hostname);
    if (
      endpoint.protocol !== "https:" &&
      !(local && endpoint.protocol === "http:")
    )
      issues.push("export endpoint must use HTTPS outside local development");
  } catch {
    issues.push("export endpoint is malformed");
  }
  const ratio = Number(input.traceSampleRatio ?? 0.1);
  if (!Number.isFinite(ratio) || ratio < 0 || ratio > 1)
    issues.push("trace sample ratio must be between 0 and 1");
  if (!boundedInteger(input.exportIntervalMs ?? 5000, 1000, 60000))
    issues.push("export interval must be between 1000 and 60000 milliseconds");
  if (!boundedInteger(input.maxQueuedSpans ?? 256, 16, 2048))
    issues.push("span queue must be between 16 and 2048");
  if (!boundedInteger(input.maxQueuedMetrics ?? 128, 16, 2048))
    issues.push("metric queue must be between 16 and 2048");
  const allowlist = Array.isArray(input.tracePropagationAllowlist)
    ? input.tracePropagationAllowlist.flatMap((item) => {
        try {
          return [new URL(String(item), pageUrl).origin];
        } catch {
          issues.push(
            "trace propagation allowlist contains a malformed origin",
          );
          return [];
        }
      })
    : [];
  if (issues.length)
    return { config: { ...disabledObservabilityConfig }, valid: false, issues };
  return {
    valid: true,
    issues: [],
    config: {
      ...disabledObservabilityConfig,
      ...(input as Partial<BrowserObservabilityConfig>),
      enabled: true,
      otlpHttpEndpoint: endpoint!.href,
      traceSampleRatio: ratio,
      tracePropagationAllowlist: [...new Set(allowlist)],
      exportIntervalMs: Number(input.exportIntervalMs ?? 5000),
      maxQueuedSpans: Number(input.maxQueuedSpans ?? 256),
      maxQueuedMetrics: Number(input.maxQueuedMetrics ?? 128),
    },
  };
}

export function runtimeObservabilityConfig() {
  return parseObservabilityConfig(window.__DATAOBS_CONFIG__?.observability);
}
