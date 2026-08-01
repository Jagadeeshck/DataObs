export type VitalName = "LCP" | "INP" | "CLS" | "FCP" | "TTFB" | "long-task";
type Diagnostics = {
  configurationLoaded: boolean;
  telemetryEnabled: boolean;
  configurationValid: boolean;
  configurationIssues: string[];
  endpointOrigin?: string;
  sampleRatio: number;
  currentRouteId: string;
  lastExportStatus: "never" | "success" | "failed" | "backoff";
  queuedSpans: number;
  droppedEvents: number;
  lastErrorFingerprint?: string;
  vitals: Partial<Record<VitalName, { value: number; unit: string }>>;
};
const initial: Diagnostics = {
  configurationLoaded: false,
  telemetryEnabled: false,
  configurationValid: true,
  configurationIssues: [],
  sampleRatio: 0,
  currentRouteId: "unknown",
  lastExportStatus: "never",
  queuedSpans: 0,
  droppedEvents: 0,
  vitals: {},
};
let state: Diagnostics = structuredClone(initial);
const listeners = new Set<() => void>();
export const diagnostics = {
  snapshot: () => structuredClone(state),
  update: (value: Partial<Diagnostics>) => {
    state = { ...state, ...value };
    listeners.forEach((listener) => listener());
  },
  reset: () => {
    state = structuredClone(initial);
    listeners.forEach((listener) => listener());
  },
  subscribe: (listener: () => void) => {
    listeners.add(listener);
    return () => listeners.delete(listener);
  },
};

export function safeDiagnosticsCopy() {
  const value = diagnostics.snapshot();
  return JSON.stringify(
    {
      consoleVersion:
        document.documentElement.dataset.consoleVersion ?? "unknown",
      buildSha: document.documentElement.dataset.buildSha ?? "unknown",
      telemetryEnabled: value.telemetryEnabled,
      configurationLoaded: value.configurationLoaded,
      configurationValid: value.configurationValid,
      endpointOrigin: value.endpointOrigin,
      sampleRatio: value.sampleRatio,
      currentRouteId: value.currentRouteId,
      connectivity: navigator.onLine ? "online" : "offline",
      lastExportStatus: value.lastExportStatus,
      queuedSpans: value.queuedSpans,
      droppedEvents: value.droppedEvents,
      lastErrorFingerprint: value.lastErrorFingerprint,
      vitals: value.vitals,
      performanceObserver: "PerformanceObserver" in window,
      serviceWorker: "serviceWorker" in navigator ? "supported" : "unsupported",
    },
    null,
    2,
  );
}
