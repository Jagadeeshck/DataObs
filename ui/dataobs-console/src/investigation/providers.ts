import { incidentsApi } from "../api/incidents";
import { pathwaysApi } from "../api/pathways";
import { qualityApi, type Evaluation, type Finding } from "../api/quality";
import { api } from "../api";
import type { InvestigationEvidence, InvestigationProvider } from "./types";

export const incidentProvider: InvestigationProvider = {
  id: "incident-timeline",
  capabilityId: "incidents",
  ownerTeam: "team-3",
  supports: ["incident"],
  requiredPermission: "incidents:read",
  maximumEvents: 25,
  maximumLookback: "7d",
  timeoutMs: 2000,
  evidenceTypes: ["incident", "incident_timeline_event"],
  isAvailable: () => true,
  async collect(r, signal) {
    const [detail, timeline] = await Promise.all([
      incidentsApi.detail(r.tenant, r.environment, r.anchor.entityId, signal),
      incidentsApi.timeline(r.tenant, r.environment, r.anchor.entityId, signal),
    ]);
    const evidence: InvestigationEvidence[] = timeline.items
      .slice(0, 24)
      .map((x) => ({
        key: `incident:${x.event_id}`,
        type: "incident_timeline_event",
        capabilityId: "incidents",
        ownerTeam: "team-3" as const,
        effectiveAt: x.timestamp,
        state: "available" as const,
        severity: detail.severity,
        title: x.summary,
        summary: x.event_type,
        entityType: "incident" as const,
        entityId: detail.id,
        provenance:
          x.actor === "system"
            ? ("system_state" as const)
            : ("user_action" as const),
        routeId: "incident-workbench",
        routeParameters: { incidentId: detail.id },
        requestId: detail.request_id,
      }));
    evidence.unshift({
      key: `incident:${detail.id}`,
      type: "incident",
      capabilityId: "incidents",
      ownerTeam: "team-3",
      effectiveAt: detail.opened_at ?? undefined,
      observedAt: detail.last_observed_at ?? undefined,
      state: detail.data_status === "complete" ? "available" : "partial",
      severity: detail.severity,
      title: detail.title,
      summary: `${detail.state}; ${detail.evidence_coverage} evidence coverage`,
      entityType: "incident",
      entityId: detail.id,
      provenance: "observed",
      routeId: "incident-workbench",
      routeParameters: { incidentId: detail.id },
      requestId: detail.request_id,
    });
    return {
      evidence,
      outcome: evidence.length ? "complete" : "empty",
      related: detail.affected_assets.slice(0, 25).map((id) => ({
        key: `asset:${id}`,
        entityType: "asset",
        entityId: id,
        relation: "affected_by",
        routeId: "asset-360",
        routeParameters: { assetId: id },
      })),
    };
  },
};
export const pathwayProvider: InvestigationProvider = {
  id: "pathway-health",
  capabilityId: "pathways",
  ownerTeam: "team-1",
  supports: ["pathway"],
  requiredPermission: "pathways:read",
  maximumEvents: 25,
  maximumLookback: "7d",
  timeoutMs: 2000,
  evidenceTypes: ["pathway_health", "lineage_relationship"],
  isAvailable: () => true,
  async collect(r, signal) {
    const [detail, health, topology] = await Promise.all([
      pathwaysApi.detail(r.tenant, r.environment, r.anchor.entityId, signal),
      pathwaysApi.health(r.tenant, r.environment, r.anchor.entityId, signal),
      pathwaysApi.topology(r.tenant, r.environment, r.anchor.entityId, signal),
    ]);
    return {
      evidence: [
        {
          key: `pathway:${detail.pathway_id}:health`,
          type: "pathway_health",
          capabilityId: "pathways",
          ownerTeam: "team-1",
          observedAt: health.observed_at ?? detail.last_seen,
          state: health.data_status === "complete" ? "available" : "partial",
          severity: health.health,
          title: `Pathway health: ${health.health}`,
          entityType: "pathway",
          entityId: detail.pathway_id,
          confidence: health.confidence ?? undefined,
          provenance: "derived",
          routeId: "pathway-360",
          routeParameters: { pathwayId: detail.pathway_id },
          requestId: health.request_id,
        },
      ],
      related: topology.nodes.slice(0, 49).map((node) => ({
        key: `${node.node_type}:${node.node_id}`,
        entityType: "asset" as const,
        entityId: node.node_id,
        label: node.name,
        relation: "contains" as const,
        routeId: "asset-360",
        routeParameters: { assetId: node.node_id },
      })),
      truncated: topology.nodes.length > 49,
    };
  },
};
export const qualityProvider: InvestigationProvider = {
  id: "quality-monitor",
  capabilityId: "quality",
  ownerTeam: "team-4",
  supports: ["monitor"],
  requiredPermission: "quality:read",
  maximumEvents: 25,
  maximumLookback: "7d",
  timeoutMs: 2000,
  evidenceTypes: ["monitor_evaluation", "quality_finding"],
  isAvailable: () => true,
  async collect(r, signal) {
    const [monitor, evaluations, findings] = await Promise.all([
      qualityApi.monitor(r.tenant, r.environment, r.anchor.entityId, signal),
      qualityApi.section<Evaluation>(
        r.tenant,
        r.environment,
        r.anchor.entityId,
        "evaluations",
        signal,
      ),
      qualityApi.section<Finding>(
        r.tenant,
        r.environment,
        r.anchor.entityId,
        "findings",
        signal,
      ),
    ]);
    const evidence: InvestigationEvidence[] = evaluations.data.items
      .slice(0, 12)
      .map((x) => ({
        key: `evaluation:${x.evaluation_id}`,
        type: "monitor_evaluation",
        capabilityId: "quality",
        ownerTeam: "team-4" as const,
        effectiveAt: x.evaluated_at,
        observedAt: x.observation.observed_at,
        state: x.missing_inputs.length
          ? ("partial" as const)
          : ("available" as const),
        severity: x.breached ? monitor.data.alert.severity : "info",
        title: x.breached ? "Monitor threshold breached" : "Monitor evaluation",
        summary: x.observation.missing_data
          ? "Input data missing"
          : `Observed value ${x.observation.value ?? "missing"}`,
        entityType: "monitor" as const,
        entityId: monitor.data.id,
        confidence: x.confidence,
        provenance: "measured" as const,
        routeId: "monitor-360",
        routeParameters: { monitorId: monitor.data.id },
        requestId: evaluations.requestId,
      }));
    evidence.push(
      ...findings.data.items.slice(0, 12).map((x) => ({
        key: `finding:${x.finding_id}`,
        type: "quality_finding",
        capabilityId: "quality",
        ownerTeam: "team-4" as const,
        state: "available" as const,
        severity: x.severity,
        title: `Quality finding: ${x.state}`,
        entityType: "monitor" as const,
        entityId: monitor.data.id,
        provenance: "derived" as const,
        routeId: "monitor-360",
        routeParameters: { monitorId: monitor.data.id },
        requestId: findings.requestId,
      })),
    );
    return { evidence };
  },
};
export const entityProvider: InvestigationProvider = {
  id: "entity-state",
  capabilityId: "jobs-assets",
  ownerTeam: "team-2",
  supports: ["job", "run", "asset", "data_product"],
  maximumEvents: 1,
  maximumLookback: "7d",
  timeoutMs: 2000,
  evidenceTypes: ["entity_status", "job_run_failure"],
  isAvailable: () => true,
  async collect(r, signal) {
    const value =
      r.anchor.entityType === "job" || r.anchor.entityType === "run"
        ? await api.entity(
            r.tenant,
            r.environment,
            r.anchor.entityType,
            r.anchor.entityId,
            signal,
          )
        : r.anchor.entityType === "data_product"
          ? (
              await api.dataProduct(
                r.tenant,
                r.environment,
                r.anchor.entityId,
                signal,
              )
            ).product
          : ((
              await api.assets(
                r.tenant,
                r.environment,
                r.anchor.entityId,
                signal,
              )
            ).items.find((item) => item.id === r.anchor.entityId) ?? {});
    const state = String(
      value.state ?? value.status ?? value.health ?? "unknown",
    );
    const at =
      String(
        value.finished_at ?? value.updated_at ?? value.observed_at ?? "",
      ) || undefined;
    return {
      evidence: [
        {
          key: `entity:${r.anchor.entityType}:${r.anchor.entityId}`,
          type: state.toLowerCase().includes("fail")
            ? "job_run_failure"
            : "entity_status",
          capabilityId:
            r.anchor.entityType === "asset"
              ? "assets"
              : r.anchor.entityType === "data_product"
                ? "data-products"
                : "jobs",
          ownerTeam: "team-2",
          effectiveAt: at,
          state: state === "unknown" ? "unknown" : "available",
          severity: state.toLowerCase().includes("fail")
            ? "critical"
            : undefined,
          title: `${r.anchor.entityType.replaceAll("_", " ")} state: ${state}`,
          entityType: r.anchor.entityType,
          entityId: r.anchor.entityId,
          provenance: "system_state",
          routeId: r.anchor.routeId,
          routeParameters: r.anchor.routeParameters,
        },
      ],
    };
  },
};
export const investigationProviders = [
  incidentProvider,
  pathwayProvider,
  qualityProvider,
  entityProvider,
] as const;
