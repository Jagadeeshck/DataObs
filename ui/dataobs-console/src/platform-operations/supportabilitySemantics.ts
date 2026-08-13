const KNOWN_STATES = new Set([
  "supported",
  "unsupported",
  "unvalidated",
  "degraded",
  "blocked",
  "unknown",
  "healthy",
  "unhealthy",
  "disabled",
  "normal",
  "planned",
  "active",
  "recovering",
  "ready",
  "not_ready",
  "partial",
  "go",
  "no_go",
  "pass",
  "fail",
  "missing",
  "stale",
]);

export function evidenceLabel(value?: string): string {
  if (!value) return "Unknown — authoritative evidence unavailable";
  const normalized = value.trim().toLowerCase().replaceAll("-", "_");
  if (!KNOWN_STATES.has(normalized)) return value;
  return normalized.toUpperCase().replaceAll("_", " ");
}

export function isBlockingState(value?: string): boolean {
  return ["blocked", "fail", "failed", "not_ready", "no_go"].includes(
    value?.toLowerCase() ?? "",
  );
}

export function freshnessPresentation(value?: string) {
  const state = value?.toLowerCase();
  if (state === "stale") return "Current evidence: Stale";
  if (!state)
    return "Freshness unknown — no timestamp or freshness evidence supplied";
  return `Evidence freshness: ${evidenceLabel(value)}`;
}
