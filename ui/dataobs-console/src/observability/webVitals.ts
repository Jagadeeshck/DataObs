import { trace } from "@opentelemetry/api";
import { onCLS, onFCP, onINP, onLCP, onTTFB, type Metric } from "web-vitals";
import type { BrowserObservabilityConfig } from "./config";
import { safeAttributes } from "./attributePolicy";
import { diagnostics, type VitalName } from "./diagnostics";

function record(metric: Metric) {
  const unit = metric.name === "CLS" ? "1" : "ms";
  diagnostics.update({
    vitals: {
      ...diagnostics.snapshot().vitals,
      [metric.name]: { value: metric.value, unit },
    },
  });
  const span = trace
    .getTracer("dataobs-console")
    .startSpan("console.ux.metric", {
      attributes: safeAttributes({
        "dataobs.console.metric_name": metric.name,
        "dataobs.console.metric_value": metric.value,
        "dataobs.console.metric_unit": unit,
      }),
    });
  span.end();
}

export function startPerformanceCapture(config: BrowserObservabilityConfig) {
  if (config.captureWebVitals)
    [onCLS, onFCP, onINP, onLCP, onTTFB].forEach((observe) => observe(record));
  if (!config.captureLongTasks || !("PerformanceObserver" in window)) return;
  try {
    let count = 0;
    let total = 0;
    let longest = 0;
    const observer = new PerformanceObserver((list) => {
      for (const entry of list.getEntries().slice(0, 25)) {
        count += 1;
        total += entry.duration;
        longest = Math.max(longest, entry.duration);
      }
      const value = { value: Math.round(total), unit: "ms" };
      diagnostics.update({
        vitals: {
          ...diagnostics.snapshot().vitals,
          ["long-task" as VitalName]: value,
        },
      });
      if (count >= 100) observer.disconnect();
    });
    observer.observe({ type: "longtask", buffered: true });
  } catch {
    /* unsupported observers are intentionally fail-open */
  }
}
