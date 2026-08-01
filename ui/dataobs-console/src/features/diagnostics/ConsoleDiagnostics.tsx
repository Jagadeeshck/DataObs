import { useSyncExternalStore, useState } from "react";
import { Link } from "react-router-dom";
import { useProductContext } from "../../state/context";
import { captureError } from "../../observability";
import {
  diagnostics,
  safeDiagnosticsCopy,
} from "../../observability/diagnostics";

export function ConsoleDiagnostics() {
  const { identity } = useProductContext();
  const state = useSyncExternalStore(
    diagnostics.subscribe,
    diagnostics.snapshot,
  );
  const [copyStatus, setCopyStatus] = useState("");
  if (!identity?.permissions.includes("console:admin"))
    return (
      <main id="main-content" className="route-state">
        <h1>Access denied</h1>
        <p>Console diagnostics requires administrative support permission.</p>
        <Link to="/">Return to Command Center</Link>
      </main>
    );
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(safeDiagnosticsCopy());
      setCopyStatus("Safe diagnostics copied.");
    } catch {
      setCopyStatus("Copy was unavailable. No diagnostics left the browser.");
    }
  };
  const connectivity = async () => {
    const origin = state.endpointOrigin;
    if (!origin) return diagnostics.update({ lastExportStatus: "failed" });
    try {
      await fetch(origin, {
        method: "HEAD",
        credentials: "omit",
        signal: AbortSignal.timeout(3000),
      });
      diagnostics.update({ lastExportStatus: "success" });
    } catch {
      diagnostics.update({ lastExportStatus: "failed" });
    }
  };
  return (
    <main id="main-content" className="page">
      <header>
        <h1>Console diagnostics</h1>
        <p>
          Privacy-safe current-session health. Identity, tenant data, tokens and
          payloads are never shown.
        </p>
      </header>
      {!state.telemetryEnabled && (
        <p role="status" className="data-status partial">
          Browser telemetry is disabled.
        </p>
      )}
      <dl className="details-grid">
        <div>
          <dt>Configuration</dt>
          <dd>{state.configurationValid ? "valid" : "invalid (disabled)"}</dd>
        </div>
        <div>
          <dt>Telemetry</dt>
          <dd>{state.telemetryEnabled ? "enabled" : "disabled"}</dd>
        </div>
        <div>
          <dt>Collector origin</dt>
          <dd>{state.endpointOrigin ?? "not configured"}</dd>
        </div>
        <div>
          <dt>Sampling ratio</dt>
          <dd>{state.sampleRatio}</dd>
        </div>
        <div>
          <dt>Current route</dt>
          <dd>{state.currentRouteId}</dd>
        </div>
        <div>
          <dt>Connectivity</dt>
          <dd>{navigator.onLine ? "online" : "offline"}</dd>
        </div>
        <div>
          <dt>Last export</dt>
          <dd>{state.lastExportStatus}</dd>
        </div>
        <div>
          <dt>Queue / dropped</dt>
          <dd>
            {state.queuedSpans} / {state.droppedEvents}
          </dd>
        </div>
        <div>
          <dt>Last error fingerprint</dt>
          <dd>{state.lastErrorFingerprint ?? "none"}</dd>
        </div>
        <div>
          <dt>Web Vitals</dt>
          <dd>
            {Object.entries(state.vitals)
              .map(([name, metric]) => `${name} ${metric.value}${metric.unit}`)
              .join(", ") || "not observed"}
          </dd>
        </div>
      </dl>
      <div className="button-row">
        <button onClick={() => void copy()}>Copy safe diagnostics</button>
        <button onClick={() => diagnostics.reset()}>
          Reset local diagnostics
        </button>
        <button
          onClick={() =>
            captureError(
              new Error("safe synthetic diagnostic"),
              "diagnostic-test",
              "console-diagnostics",
            )
          }
        >
          Send safe test event
        </button>
        <button onClick={() => void connectivity()}>
          Test collector connectivity
        </button>
      </div>
      <p role="status" aria-live="polite">
        {copyStatus}
      </p>
    </main>
  );
}
