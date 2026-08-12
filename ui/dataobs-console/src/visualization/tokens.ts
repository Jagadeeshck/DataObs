export const visualizationLimits = {
  timeSeriesPointsPerSeries: 2_000,
  dashboardPointsPerSeries: 500,
  topologyNodes: 100,
  topologyEdges: 200,
} as const;
export const semanticTokens = {
  health: {
    healthy: "var(--viz-health-healthy)",
    warning: "var(--viz-health-warning)",
    critical: "var(--viz-health-critical)",
    unknown: "var(--viz-health-unknown)",
  },
  evidence: {
    measured: "var(--viz-evidence-measured)",
    estimated: "var(--viz-evidence-estimated)",
    inferred: "var(--viz-evidence-inferred)",
    forecast: "var(--viz-evidence-forecast)",
  },
  availability: {
    available: "var(--viz-available)",
    partial: "var(--viz-partial)",
    stale: "var(--viz-stale)",
    missing: "var(--viz-missing)",
    unknown: "var(--viz-unknown)",
    unavailable: "var(--viz-unavailable)",
  },
} as const;
