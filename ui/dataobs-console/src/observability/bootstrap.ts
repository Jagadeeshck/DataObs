import { trace, SpanStatusCode, type Span } from "@opentelemetry/api";
import { OTLPTraceExporter } from "@opentelemetry/exporter-trace-otlp-http";
import { registerInstrumentations } from "@opentelemetry/instrumentation";
import { DocumentLoadInstrumentation } from "@opentelemetry/instrumentation-document-load";
import { FetchInstrumentation } from "@opentelemetry/instrumentation-fetch";
import { resourceFromAttributes } from "@opentelemetry/resources";
import {
  BatchSpanProcessor,
  ParentBasedSampler,
  TraceIdRatioBasedSampler,
  WebTracerProvider,
} from "@opentelemetry/sdk-trace-web";
import {
  ATTR_SERVICE_NAME,
  ATTR_SERVICE_VERSION,
  ATTR_DEPLOYMENT_ENVIRONMENT_NAME,
} from "@opentelemetry/semantic-conventions";
import {
  runtimeObservabilityConfig,
  type BrowserObservabilityConfig,
} from "./config";
import { diagnostics } from "./diagnostics";
import { installErrorCapture } from "./errors";
import { startPerformanceCapture } from "./webVitals";

let initialization: Promise<BrowserObservabilityConfig> | undefined;
let startupSpan: Span | undefined;

export function initializeObservability(): Promise<BrowserObservabilityConfig> {
  if (initialization) return initialization;
  initialization = Promise.resolve().then(() => {
    const parsed = runtimeObservabilityConfig();
    const config = parsed.config;
    diagnostics.update({
      configurationLoaded: Boolean(window.__DATAOBS_CONFIG__),
      telemetryEnabled: config.enabled,
      configurationValid: parsed.valid,
      configurationIssues: parsed.issues,
      endpointOrigin: config.enabled
        ? new URL(config.otlpHttpEndpoint).origin
        : undefined,
      sampleRatio: config.enabled ? config.traceSampleRatio : 0,
    });
    installErrorCapture(config);
    if (!config.enabled) return config;
    try {
      const exporter = new OTLPTraceExporter({
        url: config.otlpHttpEndpoint,
        timeoutMillis: Math.min(config.exportIntervalMs, 10000),
      });
      const provider = new WebTracerProvider({
        resource: resourceFromAttributes({
          [ATTR_SERVICE_NAME]: config.serviceName,
          [ATTR_SERVICE_VERSION]: config.serviceVersion,
          [ATTR_DEPLOYMENT_ENVIRONMENT_NAME]: config.deploymentEnvironment,
        }),
        sampler: new ParentBasedSampler({
          root: new TraceIdRatioBasedSampler(config.traceSampleRatio),
        }),
        spanProcessors: [
          new BatchSpanProcessor(exporter, {
            maxQueueSize: config.maxQueuedSpans,
            scheduledDelayMillis: config.exportIntervalMs,
            maxExportBatchSize: Math.min(64, config.maxQueuedSpans),
            exportTimeoutMillis: Math.min(config.exportIntervalMs, 10000),
          }),
        ],
      });
      provider.register();
      const allowed = config.tracePropagationAllowlist.map(
        (origin) =>
          new RegExp(
            `^${origin.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}(?:/|$)`,
          ),
      );
      registerInstrumentations({
        instrumentations: [
          new DocumentLoadInstrumentation(),
          new FetchInstrumentation({
            // Shared transport owns privacy-safe spans. Automatic fetch spans
            // are suppressed because they otherwise contain raw URLs.
            ignoreUrls: [/.*/],
            propagateTraceHeaderCorsUrls: config.propagateTraceHeaders
              ? allowed
              : [],
            clearTimingResources: true,
          }),
        ],
      });
      startupSpan = trace
        .getTracer("dataobs-console")
        .startSpan("console.startup");
      startupSpan.addEvent("observability.initialized");
      startPerformanceCapture(config);
      document.addEventListener("visibilitychange", () => {
        if (document.visibilityState === "hidden")
          void provider
            .forceFlush()
            .catch(() => diagnostics.update({ lastExportStatus: "failed" }));
      });
    } catch {
      diagnostics.update({
        telemetryEnabled: false,
        lastExportStatus: "failed",
      });
    }
    return config;
  });
  return initialization;
}

export function startupEvent(name: string) {
  startupSpan?.addEvent(name);
}
export function finishStartup() {
  if (!startupSpan) return;
  startupSpan.setStatus({ code: SpanStatusCode.OK });
  startupSpan.end();
  startupSpan = undefined;
}

export function resetObservabilityForTesting() {
  initialization = undefined;
  startupSpan = undefined;
}
