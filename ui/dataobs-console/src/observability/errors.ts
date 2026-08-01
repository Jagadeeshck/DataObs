import { SpanStatusCode, trace } from "@opentelemetry/api";
import type { BrowserObservabilityConfig } from "./config";
import { safeAttributes } from "./attributePolicy";
import { diagnostics } from "./diagnostics";
import { fingerprint, redact } from "./redaction";

const duplicates = new Map<string, number>();
let windowStarted = 0;
let events = 0;
const MAX_EVENTS_PER_MINUTE = 20;

export function captureError(
  error: unknown,
  category: string,
  stableContext = "console",
) {
  const type = error instanceof Error ? error.name : "UnknownError";
  const safeMessage = redact(error);
  const id = fingerprint([category, type, stableContext, safeMessage]);
  const now = Date.now();
  if (now - windowStarted > 60_000) {
    windowStarted = now;
    events = 0;
    duplicates.clear();
  }
  if (
    events >= MAX_EVENTS_PER_MINUTE ||
    now - (duplicates.get(id) ?? 0) < 30_000
  ) {
    diagnostics.update({
      droppedEvents: diagnostics.snapshot().droppedEvents + 1,
    });
    return id;
  }
  events += 1;
  duplicates.set(id, now);
  diagnostics.update({ lastErrorFingerprint: id });
  const span = trace.getTracer("dataobs-console").startSpan("console.error", {
    attributes: safeAttributes({
      "dataobs.console.error_category": category,
      "dataobs.console.error_fingerprint": id,
      "error.type": type,
    }),
  });
  span.addEvent("exception", {
    "exception.type": type,
    "exception.message": safeMessage,
  });
  span.setStatus({ code: SpanStatusCode.ERROR });
  span.end();
  return id;
}

let installed = false;
export function installErrorCapture(config: BrowserObservabilityConfig) {
  if (installed || !config.enabled) return;
  installed = true;
  window.addEventListener("error", (event) =>
    captureError(
      event.error ?? event.message,
      /chunk|module|import/i.test(event.message) ? "chunk-load" : "window",
      "global",
    ),
  );
  window.addEventListener("unhandledrejection", (event) =>
    captureError(event.reason, "unhandled-rejection", "global"),
  );
}

export function resetErrorLimitsForTesting() {
  duplicates.clear();
  events = 0;
  windowStarted = 0;
}
