import { INVESTIGATION_LIMITS, type InvestigationAnchor } from "./types";
export function togglePin(
  pins: InvestigationAnchor[],
  anchor: InvestigationAnchor,
) {
  const exists = pins.some(
    (p) => p.entityType === anchor.entityType && p.entityId === anchor.entityId,
  );
  return exists
    ? pins.filter(
        (p) =>
          p.entityType !== anchor.entityType || p.entityId !== anchor.entityId,
      )
    : [...pins, anchor].slice(-INVESTIGATION_LIMITS.pins);
}
export function contextChanged(
  previous: { tenant: string; environment: string },
  next: { tenant: string; environment: string },
) {
  return (
    previous.tenant !== next.tenant || previous.environment !== next.environment
  );
}
