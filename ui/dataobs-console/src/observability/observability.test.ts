// @vitest-environment jsdom
import { beforeEach, describe, expect, it, vi } from "vitest";
import { parseObservabilityConfig } from "./config";
import { safeAttributes } from "./attributePolicy";
import { fingerprint, redact } from "./redaction";
import { apiRouteTemplate, instrumentedFetch } from "./requests";
import { diagnostics, safeDiagnosticsCopy } from "./diagnostics";
import { captureError, resetErrorLimitsForTesting } from "./errors";

describe("browser observability safety contract", () => {
  beforeEach(() => {
    diagnostics.reset();
    resetErrorLimitsForTesting();
    vi.restoreAllMocks();
  });

  it("is disabled by default", () => {
    expect(parseObservabilityConfig(undefined).config.enabled).toBe(false);
  });
  it("validates a same-origin runtime endpoint and bounds", () => {
    const result = parseObservabilityConfig(
      {
        enabled: true,
        otlpHttpEndpoint: "/otel/v1/traces",
        traceSampleRatio: 0.25,
        exportIntervalMs: 2000,
        maxQueuedSpans: 32,
        maxQueuedMetrics: 32,
      },
      "https://console.example.test/",
    );
    expect(result.valid).toBe(true);
    expect(result.config.otlpHttpEndpoint).toBe(
      "https://console.example.test/otel/v1/traces",
    );
  });
  it.each([
    [
      {
        enabled: true,
        otlpHttpEndpoint: "http://collector.example.test",
        traceSampleRatio: 0.2,
      },
      "HTTPS",
    ],
    [
      {
        enabled: true,
        otlpHttpEndpoint: "https://user:secret@collector.test/v1",
        traceSampleRatio: 0.2,
      },
      "credentials",
    ],
    [
      {
        enabled: true,
        otlpHttpEndpoint: "https://collector.test/v1?token=x",
        traceSampleRatio: 0.2,
      },
      "query",
    ],
    [{ enabled: true, otlpHttpEndpoint: "/v1", traceSampleRatio: 2 }, "ratio"],
  ])("fails closed for invalid configuration", (input, issue) => {
    const result = parseObservabilityConfig(
      input,
      "https://console.example.test/",
    );
    expect(result.valid).toBe(false);
    expect(result.config.enabled).toBe(false);
    expect(result.issues.join(" ")).toMatch(new RegExp(issue, "i"));
  });
  it("normalises API routes without query strings or dynamic IDs", () => {
    expect(apiRouteTemplate("/api/v1/incidents/12345?search=customer")).toBe(
      "/api/v1/incidents/:id",
    );
    expect(
      apiRouteTemplate(
        "/api/v1/assets/0123456789abcdef0123456789abcdef?token=no",
      ),
    ).toBe("/api/v1/assets/:id");
  });
  it("redacts prohibited values and produces stable fingerprints", () => {
    const unsafe =
      "Authorization: Bearer-secret jane@example.com arn:aws:iam::123456789012:role/Admin https://x.test/a?tenant=secret 10.1.2.3";
    const safe = redact(unsafe);
    expect(safe).not.toContain("jane@example.com");
    expect(safe).not.toContain("123456789012");
    expect(safe).not.toContain("tenant=secret");
    expect(safe).not.toContain("10.1.2.3");
    expect(fingerprint([unsafe])).toBe(fingerprint([unsafe]));
  });
  it("rejects unknown attributes in tests", () => {
    expect(() => safeAttributes({ "tenant.id": "secret" })).toThrow(
      /Unknown telemetry attribute/,
    );
  });
  it("records expected abortion as cancellation without error capture", async () => {
    const controller = new AbortController();
    controller.abort();
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new DOMException("aborted", "AbortError")),
    );
    await expect(
      instrumentedFetch("/api/v1/assets/42", { signal: controller.signal }),
    ).rejects.toThrow("aborted");
    expect(diagnostics.snapshot().lastErrorFingerprint).toBeUndefined();
  });
  it("suppresses duplicate errors and rate limits", () => {
    const first = captureError(new Error("same"), "window");
    const second = captureError(new Error("same"), "window");
    expect(second).toBe(first);
    expect(diagnostics.snapshot().droppedEvents).toBe(1);
  });
  it("copies only an explicit safe diagnostics projection", () => {
    localStorage.setItem("access_token", "must-not-copy");
    document.cookie = "tenant=must-not-copy";
    expect(safeDiagnosticsCopy()).not.toContain("must-not-copy");
  });
});
