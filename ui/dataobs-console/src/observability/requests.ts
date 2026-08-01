import {
  context,
  propagation,
  SpanStatusCode,
  trace,
} from "@opentelemetry/api";
import { safeAttributes } from "./attributePolicy";
import { runtimeObservabilityConfig } from "./config";
import { captureError } from "./errors";

export const apiRouteTemplate = (path: string) => {
  const pathname = new URL(path, location.origin).pathname;
  return pathname
    .replace(/\b[0-9a-f]{8}-[0-9a-f-]{27,}\b/gi, ":id")
    .replace(/\/[0-9]+(?=\/|$)/g, "/:id")
    .replace(/\/[A-Za-z0-9_-]{20,}(?=\/|$)/g, "/:id")
    .slice(0, 120);
};

export async function instrumentedFetch(
  input: RequestInfo | URL,
  init: RequestInit = {},
) {
  const url =
    typeof input === "string"
      ? input
      : input instanceof URL
        ? input.href
        : input.url;
  const method = (
    init.method ?? (input instanceof Request ? input.method : "GET")
  ).toUpperCase();
  const span = trace
    .getTracer("dataobs-console")
    .startSpan("console.api.request", {
      attributes: safeAttributes({
        "http.request.method": method,
        "url.template": apiRouteTemplate(url),
      }),
    });
  try {
    const config = runtimeObservabilityConfig().config;
    let requestInit = init;
    try {
      const origin = new URL(url, location.href).origin;
      if (
        config.enabled &&
        config.propagateTraceHeaders &&
        config.tracePropagationAllowlist.includes(origin)
      ) {
        const headers = new Headers(
          init.headers ??
            (input instanceof Request ? input.headers : undefined),
        );
        const carrier: Record<string, string> = {};
        propagation.inject(context.active(), carrier);
        Object.entries(carrier).forEach(([name, value]) =>
          headers.set(name, value),
        );
        requestInit = { ...init, headers };
      }
    } catch {
      /* malformed URLs remain the fetch implementation's concern */
    }
    const response = await fetch(input, requestInit);
    span.setAttributes(
      safeAttributes({ "http.response.status_code": response.status }),
    );
    const requestId = response.headers.get("X-Request-ID");
    if (requestId)
      span.setAttributes(
        safeAttributes({ "dataobs.console.request_id": requestId }),
      );
    if (!response.ok) span.setStatus({ code: SpanStatusCode.ERROR });
    return response;
  } catch (error) {
    if (
      init.signal?.aborted ||
      (error instanceof DOMException && error.name === "AbortError")
    )
      span.addEvent("request.cancelled");
    else {
      span.setStatus({ code: SpanStatusCode.ERROR });
      captureError(error, "api-transport", apiRouteTemplate(url));
    }
    throw error;
  } finally {
    span.end();
  }
}
