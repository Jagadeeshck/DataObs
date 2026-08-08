import type { EntityType } from "../app/entityLinks";
import { consoleRoutes, routeForPath } from "../app/routes";
import type { InvestigationAnchor } from "./types";

const entityTypes = new Set<EntityType>([
  "incident",
  "monitor",
  "job",
  "run",
  "pathway",
  "kafka_cluster",
  "topic",
  "consumer_group",
  "connector",
  "schema_subject",
  "data_product",
  "asset",
  "integration",
]);
const safe = (value: string | null, max = 512) =>
  value &&
  value.length <= max &&
  ![...value].some((character) => character.charCodeAt(0) < 32)
    ? value
    : undefined;
export function parseAnchor(
  query: URLSearchParams,
): InvestigationAnchor | undefined {
  const entityType = safe(query.get("entityType"), 40) as
    | EntityType
    | undefined;
  const entityId = safe(query.get("entityId"));
  if (!entityType || !entityTypes.has(entityType) || !entityId)
    return undefined;
  const routeId = safe(query.get("routeId"), 80);
  const route = routeId
    ? consoleRoutes.find(
        (candidate) =>
          candidate.id === routeId &&
          candidate.entityParameters?.some(
            (p) => p.entityType.replace("-", "_") === entityType,
          ),
      )
    : undefined;
  const parameter = route?.entityParameters?.[0]?.name;
  return {
    entityType,
    entityId,
    label: safe(query.get("label"), 160),
    routeId: route?.id,
    routeParameters: parameter ? { [parameter]: entityId } : undefined,
  };
}
export function safeConsoleReturn(value: string | null): string | undefined {
  if (
    !value ||
    value.length > 300 ||
    !value.startsWith("/") ||
    value.startsWith("//") ||
    value.includes("?") ||
    value.includes("#")
  )
    return;
  return routeForPath(value) ? value : undefined;
}
export function investigationPath(
  anchor: InvestigationAnchor,
  returnTo?: string,
) {
  const query = new URLSearchParams({
    entityType: anchor.entityType,
    entityId: anchor.entityId,
  });
  if (anchor.label && anchor.label !== anchor.entityId)
    query.set("label", anchor.label.slice(0, 160));
  if (anchor.routeId) query.set("routeId", anchor.routeId);
  const safeReturn = returnTo && safeConsoleReturn(returnTo);
  if (safeReturn) query.set("returnTo", safeReturn);
  return `/investigate?${query}`;
}
