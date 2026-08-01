import { buildRoutePath, routeForPath } from "./routes";
import type { TimeRange } from "../state/context";

export type InvestigationContext = {
  sourceRoute?: string;
  entityType?: string;
  entityId?: string;
  timeRange?: TimeRange;
  selectedOverlay?: string;
  selectedTab?: string;
  filterSummary?: string;
  returnRoute?: string;
};
const allowedKeys: Record<keyof InvestigationContext, string> = {
  sourceRoute: "from",
  entityType: "entityType",
  entityId: "entityId",
  timeRange: "range",
  selectedOverlay: "overlay",
  selectedTab: "tab",
  filterSummary: "filters",
  returnRoute: "returnTo",
};
export function safeReturnRoute(value?: string) {
  if (!value || !value.startsWith("/") || value.startsWith("//"))
    return undefined;
  try {
    const url = new URL(value, location.origin);
    return url.origin === location.origin && routeForPath(url.pathname)
      ? `${url.pathname}${url.search}`
      : undefined;
  } catch {
    return undefined;
  }
}
export function investigationQuery(context: InvestigationContext) {
  const query = new URLSearchParams();
  Object.entries(allowedKeys).forEach(([key, queryKey]) => {
    let value = context[key as keyof InvestigationContext];
    if (key === "returnRoute") value = safeReturnRoute(value);
    if (value) query.set(queryKey, String(value).slice(0, 200));
  });
  return query;
}
export function investigationLink(
  routeId: string,
  parameters: Record<string, string>,
  context: InvestigationContext,
) {
  const path = buildRoutePath(routeId, parameters);
  if (!path) return undefined;
  const query = investigationQuery(context).toString();
  return query ? `${path}?${query}` : path;
}
