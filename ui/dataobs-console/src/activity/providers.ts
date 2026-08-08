import { classifyAttention } from "./attentionPolicy";
import type { ActivityItem, ActivityProvider, ActivitySeverity } from "./types";

export const incidentActivityProvider: ActivityProvider = {
  id: "incident-workbench-activity",
  capabilityId: "incidents",
  ownerTeam: "team-3",
  requiredPermission: "incidents:read",
  maximumItems: 25,
  timeoutMs: 2_000,
  maximumLookbackHours: 24 * 7,
  supportedFilters: ["time_range", "severity", "state"],
  cursorModel: "opaque",
  activityTypes: ["incident_created", "incident_updated", "incident_resolved"],
  attentionSource: "explicit_presentation_mapping",
  supports: (context) => context.permissions.includes("incidents:read"),
  async load(request, signal) {
    const { incidentsApi } = await import("../api/incidents");
    const query = new URLSearchParams({
      limit: String(Math.min(request.maximumItems, 25)),
      start: request.start,
      end: request.end,
    });
    const response = await incidentsApi.list(
      request.context.tenant,
      request.context.environment,
      query,
      signal,
    );
    const items = response.items.map((incident): ActivityItem => {
      const state =
        incident.state.toLowerCase() === "resolved" ? "resolved" : "active";
      const type =
        state === "resolved"
          ? "incident_resolved"
          : incident.opened_at === incident.last_observed_at
            ? "incident_created"
            : "incident_updated";
      const item: ActivityItem = {
        key: `incident:${incident.id}:${incident.last_observed_at ?? incident.opened_at ?? "unknown"}`,
        type,
        capabilityId: "incidents",
        ownerTeam: "team-3",
        occurredAt:
          incident.last_observed_at ?? incident.opened_at ?? request.end,
        observedAt: incident.last_observed_at ?? undefined,
        severity: (["critical", "high", "medium", "low"].includes(
          incident.severity.toLowerCase(),
        )
          ? incident.severity.toLowerCase()
          : "unknown") as ActivitySeverity,
        state,
        evidenceState:
          response.data_status === "available" ? "available" : "partial",
        title: incident.title,
        summary: `${incident.affected_asset_count} affected assets`,
        entityType: "incident",
        entityId: incident.id,
        routeId: "incident-workbench",
        routeParameters: { incidentId: incident.id },
        provenance: "system_transition",
      };
      item.attention = classifyAttention(item);
      return item;
    });
    return {
      items,
      outcome: response.data_status === "available" ? "available" : "partial",
      warning: response.warnings[0],
    };
  },
};
