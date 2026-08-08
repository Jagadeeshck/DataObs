import { createElement, type ComponentType } from "react";

export type CapabilityAvailability =
  | "available"
  | "preview"
  | "not_configured"
  | "planned"
  | "unavailable";
export type NavigationGroup =
  | "Overview"
  | "Observe"
  | "Respond"
  | "Configure"
  | "System";
export type ConfigurationState =
  | "configured"
  | "optional"
  | "required"
  | "not_applicable";
export type RouteModule = Promise<{ default: ComponentType }>;

export interface EntityParameter {
  name: string;
  entityType: string;
  encode: (value: string) => string;
}
export interface ConsoleRoute {
  id: string;
  path: string;
  name: string;
  aliases: readonly string[];
  group: NavigationGroup;
  capabilityId: string;
  icon: string;
  requiredPermission?: string;
  protected: boolean;
  owner: `team-${0 | 1 | 2 | 3 | 4 | 5}`;
  availability: CapabilityAvailability;
  configuration: ConfigurationState;
  breadcrumb: string;
  parentId?: string;
  entityParameters?: readonly EntityParameter[];
  navigation: boolean;
  quickFind: boolean;
  searchEligible: boolean;
  documentTitle: string;
  loadingLabel: string;
  featureFlag?: string;
  onboardingDependency?: string;
  loader: () => RouteModule;
}

const parameter = (name: string, entityType: string): EntityParameter => ({
  name,
  entityType,
  encode: encodeURIComponent,
});
const modules = import.meta.glob([
  "../features/**/*.tsx",
  "!../features/**/*.test.tsx",
  "../auth/AuthPages.tsx",
]);
const load = (path: string, exportName: string) => async () => {
  const importer = modules[`${path}.tsx`];
  if (!importer) throw new Error(`Route module is not registered: ${path}`);
  const module = (await importer()) as Record<string, ComponentType>;
  if (!module[exportName])
    throw new Error(`Route component is not exported: ${exportName}`);
  return { default: module[exportName] };
};
const streamDetail = (kind: "topic" | "group") => async () => {
  const { Stream360 } = await import("../features/streams/Stream360");
  return { default: () => createElement(Stream360, { kind }) };
};

const route = (
  value: Partial<ConsoleRoute> &
    Pick<
      ConsoleRoute,
      "id" | "path" | "name" | "group" | "capabilityId" | "owner" | "loader"
    >,
): ConsoleRoute => ({
  aliases: [],
  icon: "·",
  protected: true,
  requiredPermission: "console:read",
  availability: "available",
  configuration: "configured",
  breadcrumb: value.name,
  navigation: false,
  quickFind: true,
  searchEligible: true,
  documentTitle: `DataObs — ${value.name}`,
  loadingLabel: `Loading ${value.name}…`,
  ...value,
});

/** Authoritative routing, navigation, breadcrumb, permission and discovery model. */
export const consoleRoutes: readonly ConsoleRoute[] = [
  route({
    id: "command-center",
    path: "/",
    name: "Command Center",
    aliases: ["home", "overview"],
    group: "Overview",
    capabilityId: "command-center",
    icon: "⌁",
    owner: "team-5",
    navigation: true,
    loader: load("../features/command-center/CommandCenter", "CommandCenter"),
  }),
  route({
    id: "activity-center",
    path: "/activity",
    name: "Activity",
    aliases: ["operator inbox", "notifications", "what changed"],
    group: "Overview",
    capabilityId: "activity",
    icon: "◉",
    owner: "team-5",
    navigation: true,
    searchEligible: false,
    loader: load("../features/activity/ActivityCenter", "ActivityCenter"),
  }),
  route({
    id: "flow",
    path: "/flow",
    name: "Data Flow",
    aliases: ["map", "topology"],
    group: "Overview",
    capabilityId: "unified-data-flow",
    icon: "⌘",
    owner: "team-5",
    navigation: true,
    loader: load("../features/flow-map/FlowMap", "FlowMap"),
  }),
  route({
    id: "global-search",
    path: "/search",
    name: "Global Search",
    aliases: ["find", "entities"],
    group: "Overview",
    capabilityId: "global-search",
    icon: "⌕",
    owner: "team-5",
    navigation: true,
    searchEligible: false,
    loader: load("../features/global-search/GlobalSearch", "GlobalSearch"),
  }),
  route({
    id: "investigation-workspace",
    path: "/investigate",
    name: "Investigation",
    aliases: ["evidence", "timeline"],
    group: "Overview",
    capabilityId: "investigation",
    icon: "⌖",
    owner: "team-5",
    navigation: true,
    searchEligible: false,
    loader: load(
      "../features/investigation/InvestigationWorkspace",
      "InvestigationWorkspace",
    ),
  }),
  route({
    id: "dashboards",
    path: "/dashboards",
    name: "Operational Dashboards",
    aliases: ["saved views", "watchlist"],
    group: "Overview",
    capabilityId: "operational-dashboards",
    icon: "▦",
    owner: "team-5",
    navigation: true,
    loader: load("../features/dashboards/Dashboards", "DashboardGallery"),
  }),
  route({
    id: "dashboard-view",
    path: "/dashboards/:dashboardId",
    name: "Operational Dashboard",
    group: "Overview",
    capabilityId: "operational-dashboards",
    owner: "team-5",
    parentId: "dashboards",
    entityParameters: [parameter("dashboardId", "dashboard")],
    quickFind: false,
    searchEligible: false,
    loader: load("../features/dashboards/Dashboards", "DashboardView"),
  }),
  route({
    id: "pathways",
    path: "/pathways",
    name: "Pathways",
    group: "Observe",
    capabilityId: "pathways",
    icon: "⇄",
    owner: "team-1",
    navigation: true,
    loader: load("../features/pathways/PathwayExplorer", "PathwayExplorer"),
  }),
  route({
    id: "pathway-360",
    path: "/pathways/:pathwayId",
    name: "Pathway",
    group: "Observe",
    capabilityId: "pathways",
    owner: "team-1",
    parentId: "pathways",
    entityParameters: [parameter("pathwayId", "pathway")],
    loader: load("../features/pathways/PathwayExplorer", "PathwayExplorer"),
  }),
  route({
    id: "assets",
    path: "/assets",
    name: "Assets",
    group: "Observe",
    capabilityId: "assets",
    icon: "◇",
    owner: "team-2",
    navigation: true,
    loader: load("../features/assets/AssetCatalog", "AssetCatalog"),
  }),
  route({
    id: "data-contracts",
    path: "/data-contracts",
    name: "Data Contracts",
    aliases: ["contracts", "schema governance"],
    group: "Observe",
    capabilityId: "data-contracts",
    icon: "▣",
    owner: "team-2",
    navigation: true,
    loader: load("../features/data-contracts/DataContracts", "DataContracts"),
  }),
  route({
    id: "data-contract-new",
    path: "/data-contracts/new",
    name: "New Data Contract",
    group: "Configure",
    capabilityId: "data-contracts",
    owner: "team-2",
    parentId: "data-contracts",
    loader: load(
      "../features/data-contracts/DataContracts",
      "ContractAuthoring",
    ),
  }),
  route({
    id: "data-contract-360",
    path: "/data-contracts/:contractId",
    name: "Data Contract",
    group: "Observe",
    capabilityId: "data-contracts",
    owner: "team-2",
    parentId: "data-contracts",
    entityParameters: [parameter("contractId", "data-contract")],
    loader: load("../features/data-contracts/DataContracts", "Contract360"),
  }),
  route({
    id: "data-contract-version",
    path: "/data-contracts/:contractId/versions/:version",
    name: "Contract Version",
    group: "Observe",
    capabilityId: "data-contracts",
    owner: "team-2",
    parentId: "data-contract-360",
    entityParameters: [
      parameter("contractId", "data-contract"),
      parameter("version", "contract-version"),
    ],
    loader: load("../features/data-contracts/DataContracts", "ContractVersion"),
  }),
  route({
    id: "asset-360",
    path: "/assets/:assetId",
    name: "Asset",
    group: "Observe",
    capabilityId: "assets",
    owner: "team-2",
    parentId: "assets",
    entityParameters: [parameter("assetId", "asset")],
    loader: load("../features/assets/Asset360", "Asset360"),
  }),
  route({
    id: "streams",
    path: "/streams",
    name: "Streams",
    aliases: ["kafka"],
    group: "Observe",
    capabilityId: "streams",
    icon: "≋",
    owner: "team-1",
    navigation: true,
    loader: load("../features/streams/StreamsInventory", "StreamsInventory"),
  }),
  route({
    id: "streams-reliability",
    path: "/streams/reliability",
    name: "Stream Reliability",
    group: "Observe",
    capabilityId: "streams",
    owner: "team-1",
    parentId: "streams",
    loader: load(
      "../features/streams/StreamsReliability",
      "StreamsReliability",
    ),
  }),
  route({
    id: "streams-intelligence",
    path: "/streams/intelligence",
    name: "Stream Intelligence",
    aliases: ["anomalies", "retention forecasts"],
    group: "Observe",
    capabilityId: "stream-intelligence",
    owner: "team-1",
    parentId: "streams",
    navigation: true,
    loader: load(
      "../features/streams/StreamIntelligence",
      "StreamIntelligence",
    ),
  }),
  route({
    id: "cluster-360",
    path: "/streams/clusters/:clusterId",
    name: "Kafka cluster",
    group: "Observe",
    capabilityId: "streams",
    owner: "team-1",
    parentId: "streams",
    entityParameters: [parameter("clusterId", "cluster")],
    loader: load("../features/streams/Cluster360", "Cluster360"),
  }),
  route({
    id: "topic-360",
    path: "/streams/topics/:streamId",
    name: "Topic",
    group: "Observe",
    capabilityId: "streams",
    owner: "team-1",
    parentId: "streams",
    entityParameters: [parameter("streamId", "topic")],
    loader: streamDetail("topic"),
  }),
  route({
    id: "consumer-group-360",
    path: "/streams/consumer-groups/:groupId",
    name: "Consumer group",
    group: "Observe",
    capabilityId: "streams",
    owner: "team-1",
    parentId: "streams",
    entityParameters: [parameter("groupId", "consumer-group")],
    loader: streamDetail("group"),
  }),
  route({
    id: "connector-360",
    path: "/streams/connectors/:connectorId",
    name: "Connector",
    group: "Observe",
    capabilityId: "streams",
    owner: "team-1",
    parentId: "streams",
    entityParameters: [parameter("connectorId", "connector")],
    loader: load("../features/streams/Connector360", "Connector360"),
  }),
  route({
    id: "schema-360",
    path: "/streams/schemas/:subjectId",
    name: "Schema",
    group: "Observe",
    capabilityId: "streams",
    owner: "team-1",
    parentId: "streams",
    entityParameters: [parameter("subjectId", "schema")],
    loader: load("../features/streams/Schema360", "Schema360"),
  }),
  route({
    id: "data-products",
    path: "/data-products",
    name: "Data Products",
    group: "Observe",
    capabilityId: "data-products",
    icon: "▣",
    owner: "team-2",
    navigation: true,
    loader: load(
      "../features/data-products/DataProductList",
      "DataProductList",
    ),
  }),
  route({
    id: "data-product-360",
    path: "/data-products/:productId",
    name: "Data product",
    group: "Observe",
    capabilityId: "data-products",
    owner: "team-2",
    parentId: "data-products",
    entityParameters: [parameter("productId", "data-product")],
    loader: load("../features/data-products/DataProduct360", "DataProduct360"),
  }),
  route({
    id: "quality",
    path: "/quality",
    name: "Data Quality",
    group: "Observe",
    capabilityId: "quality",
    icon: "✓",
    owner: "team-4",
    navigation: true,
    loader: load("../features/quality/QualityOverview", "QualityOverview"),
  }),
  route({
    id: "monitors",
    path: "/quality/monitors",
    name: "Monitors",
    group: "Observe",
    capabilityId: "quality",
    owner: "team-4",
    parentId: "quality",
    loader: load("../features/quality/MonitorInventory", "MonitorInventory"),
  }),
  route({
    id: "monitor-new",
    path: "/quality/monitors/new",
    name: "Create monitor",
    group: "Observe",
    capabilityId: "quality",
    owner: "team-4",
    parentId: "monitors",
    searchEligible: false,
    loader: load("../features/quality/MonitorAuthoring", "MonitorAuthoring"),
  }),
  route({
    id: "monitor-360",
    path: "/quality/monitors/:monitorId",
    name: "Monitor",
    group: "Observe",
    capabilityId: "quality",
    owner: "team-4",
    parentId: "monitors",
    entityParameters: [parameter("monitorId", "monitor")],
    loader: load("../features/quality/Monitor360", "Monitor360"),
  }),
  route({
    id: "jobs",
    path: "/jobs",
    name: "Jobs",
    group: "Observe",
    capabilityId: "jobs",
    icon: "▤",
    owner: "team-2",
    navigation: true,
    loader: load("../features/jobs/JobRunExplorer", "JobsInventory"),
  }),
  route({
    id: "job-360",
    path: "/jobs/:jobId",
    name: "Job",
    group: "Observe",
    capabilityId: "jobs",
    owner: "team-2",
    parentId: "jobs",
    entityParameters: [parameter("jobId", "job")],
    loader: load("../features/jobs/JobRunExplorer", "Job360"),
  }),
  route({
    id: "run-360",
    path: "/runs/:runId",
    name: "Run",
    group: "Observe",
    capabilityId: "jobs",
    owner: "team-2",
    parentId: "jobs",
    entityParameters: [parameter("runId", "run")],
    loader: load("../features/jobs/JobRunExplorer", "Run360"),
  }),
  route({
    id: "run-comparison",
    path: "/runs/compare",
    name: "Run comparison",
    group: "Observe",
    capabilityId: "jobs",
    owner: "team-2",
    parentId: "jobs",
    loader: load("../features/jobs/JobRunExplorer", "RunComparison"),
  }),
  route({
    id: "lineage",
    path: "/lineage",
    name: "Lineage",
    group: "Observe",
    capabilityId: "lineage",
    icon: "↝",
    owner: "team-2",
    navigation: true,
    loader: load("../features/lineage/LineageExplorer", "LineageExplorer"),
  }),
  route({
    id: "incidents",
    path: "/incidents",
    name: "Incidents",
    group: "Respond",
    capabilityId: "incidents",
    icon: "!",
    requiredPermission: "incidents:read",
    owner: "team-3",
    navigation: true,
    loader: load("../features/incidents/IncidentInbox", "IncidentInbox"),
  }),
  route({
    id: "incident-workbench",
    path: "/incidents/:incidentId",
    name: "Incident",
    group: "Respond",
    capabilityId: "incidents",
    requiredPermission: "incidents:read",
    owner: "team-3",
    parentId: "incidents",
    entityParameters: [parameter("incidentId", "incident")],
    loader: load("../features/incidents/IncidentDetail", "IncidentDetail"),
  }),
  route({
    id: "event-storms",
    path: "/incidents/event-storms",
    name: "Event Storms",
    group: "Respond",
    capabilityId: "incidents",
    requiredPermission: "incidents:read",
    owner: "team-3",
    parentId: "incidents",
    navigation: true,
    loader: load("../features/incidents/EventStorms", "EventStormInventory"),
  }),
  route({
    id: "event-storm-detail",
    path: "/incidents/event-storms/:floodId",
    name: "Event Storm",
    group: "Respond",
    capabilityId: "incidents",
    requiredPermission: "incidents:read",
    owner: "team-3",
    parentId: "event-storms",
    entityParameters: [parameter("floodId", "event-storm")],
    loader: load("../features/incidents/EventStorms", "EventStormDetail"),
  }),
  route({
    id: "correlation-group-detail",
    path: "/incidents/correlation-groups/:groupId",
    name: "Correlation Group",
    group: "Respond",
    capabilityId: "incidents",
    requiredPermission: "incidents:read",
    owner: "team-3",
    parentId: "incidents",
    entityParameters: [parameter("groupId", "correlation-group")],
    loader: load("../features/incidents/EventStorms", "CorrelationGroupDetail"),
  }),
  route({
    id: "integrations",
    path: "/integrations",
    name: "Integrations",
    group: "Configure",
    capabilityId: "integrations",
    icon: "+",
    requiredPermission: "integrations:read",
    owner: "team-5",
    navigation: true,
    loader: load("../features/integrations/Integrations", "Integrations"),
  }),
  route({
    id: "integration-detail",
    path: "/integrations/:integrationId",
    name: "Integration",
    group: "Configure",
    capabilityId: "integrations",
    requiredPermission: "integrations:read",
    owner: "team-5",
    parentId: "integrations",
    entityParameters: [parameter("integrationId", "integration")],
    loader: load("../features/integrations/Integrations", "IntegrationDetail"),
  }),
  route({
    id: "onboarding",
    path: "/onboarding",
    name: "Get started",
    aliases: ["setup"],
    group: "Configure",
    capabilityId: "onboarding",
    icon: "→",
    owner: "team-5",
    navigation: true,
    loader: load("../features/onboarding/Onboarding", "Onboarding"),
  }),
  route({
    id: "administration",
    path: "/administration",
    name: "Administration",
    group: "Configure",
    capabilityId: "administration-access",
    icon: "⚙",
    owner: "team-5",
    requiredPermission: "iam:read",
    navigation: true,
    loader: load(
      "../features/administration/Administration",
      "AdministrationOverview",
    ),
  }),
  route({
    id: "administration-my-access",
    path: "/administration/my-access",
    name: "My access",
    group: "Configure",
    capabilityId: "administration-access",
    owner: "team-5",
    requiredPermission: "auth:read",
    parentId: "administration",
    navigation: true,
    loader: load("../features/administration/Administration", "MyAccess"),
  }),
  route({
    id: "administration-access",
    path: "/administration/access",
    name: "Role bindings",
    group: "Configure",
    capabilityId: "administration-access",
    owner: "team-5",
    requiredPermission: "iam:read",
    parentId: "administration",
    loader: load(
      "../features/administration/Administration",
      "AccessInventory",
    ),
  }),
  route({
    id: "administration-access-new",
    path: "/administration/access/new",
    name: "Create role binding",
    group: "Configure",
    capabilityId: "administration-access",
    owner: "team-5",
    requiredPermission: "iam:write",
    parentId: "administration-access",
    quickFind: false,
    searchEligible: false,
    loader: load("../features/administration/Administration", "CreateBinding"),
  }),
  route({
    id: "administration-access-detail",
    path: "/administration/access/:bindingId",
    name: "Role binding",
    group: "Configure",
    capabilityId: "administration-access",
    owner: "team-5",
    requiredPermission: "iam:read",
    parentId: "administration-access",
    entityParameters: [parameter("bindingId", "role-binding")],
    loader: load("../features/administration/Administration", "BindingDetail"),
  }),
  route({
    id: "administration-audit",
    path: "/administration/audit",
    name: "Access audit",
    group: "Configure",
    capabilityId: "administration-access",
    owner: "team-5",
    requiredPermission: "audit:read",
    parentId: "administration",
    quickFind: false,
    searchEligible: false,
    loader: load("../features/administration/Administration", "AccessAudit"),
  }),
  route({
    id: "administration-system",
    path: "/administration/system",
    name: "System information",
    group: "Configure",
    capabilityId: "administration-access",
    owner: "team-5",
    requiredPermission: "auth:read",
    parentId: "administration",
    loader: load(
      "../features/administration/Administration",
      "SystemInformation",
    ),
  }),
  route({
    id: "administration-preferences",
    path: "/administration/preferences",
    name: "Console preferences",
    group: "Configure",
    capabilityId: "administration-access",
    owner: "team-5",
    requiredPermission: "auth:read",
    parentId: "administration",
    loader: load("../features/administration/Administration", "Preferences"),
  }),
  route({
    id: "console-diagnostics",
    path: "/diagnostics/console",
    name: "Console diagnostics",
    group: "System",
    capabilityId: "console-observability",
    owner: "team-5",
    requiredPermission: "console:admin",
    navigation: false,
    quickFind: false,
    searchEligible: false,
    loader: load(
      "../features/diagnostics/ConsoleDiagnostics",
      "ConsoleDiagnostics",
    ),
  }),
  route({
    id: "login",
    path: "/login",
    name: "Sign in",
    group: "System",
    capabilityId: "authentication",
    owner: "team-5",
    protected: false,
    requiredPermission: undefined,
    quickFind: false,
    searchEligible: false,
    loader: load("../auth/AuthPages", "Login"),
  }),
  route({
    id: "auth-callback",
    path: "/auth/callback",
    name: "Authentication callback",
    group: "System",
    capabilityId: "authentication",
    owner: "team-5",
    protected: false,
    requiredPermission: undefined,
    quickFind: false,
    searchEligible: false,
    loader: load("../auth/AuthPages", "Callback"),
  }),
  route({
    id: "logout",
    path: "/logout",
    name: "Sign out",
    group: "System",
    capabilityId: "authentication",
    owner: "team-5",
    protected: false,
    requiredPermission: undefined,
    quickFind: false,
    searchEligible: false,
    loader: load("../auth/AuthPages", "Logout"),
  }),
  route({
    id: "unauthorised",
    path: "/unauthorised",
    name: "Unauthorised",
    group: "System",
    capabilityId: "shell",
    owner: "team-5",
    protected: false,
    requiredPermission: undefined,
    quickFind: false,
    searchEligible: false,
    loader: load("../auth/AuthPages", "Unauthorised"),
  }),
] as const;

export interface EffectiveRouteState {
  availability: CapabilityAvailability;
  authorised: boolean;
  configuration: ConfigurationState;
  actionable: boolean;
}
export function resolveRouteState(
  route: ConsoleRoute,
  permissions: readonly string[],
  capabilities?: Record<string, ConfigurationState>,
): EffectiveRouteState {
  const authorised =
    !route.requiredPermission ||
    route.requiredPermission === "console:read" ||
    permissions.includes(route.requiredPermission);
  const configuration =
    capabilities?.[route.id] ??
    capabilities?.[route.parentId ?? ""] ??
    route.configuration;
  return {
    availability: route.availability,
    authorised,
    configuration,
    actionable:
      authorised &&
      ["available", "preview"].includes(route.availability) &&
      (configuration === "configured" || configuration === "optional"),
  };
}
export function visibleRoutes(permissions: readonly string[]) {
  return consoleRoutes.filter(
    (item) =>
      !item.requiredPermission ||
      item.requiredPermission === "console:read" ||
      permissions.includes(item.requiredPermission),
  );
}
const normalise = (value: string) =>
  value !== "/" && value.endsWith("/") ? value.slice(0, -1) : value;
const matches = (pattern: string, pathname: string) =>
  new RegExp(`^${pattern.replace(/:[^/]+/g, "[^/]+")}$`).test(
    normalise(pathname),
  );
export function routeForPath(pathname: string) {
  return consoleRoutes.find((item) => matches(item.path, pathname));
}
export function buildRoutePath(
  routeId: string,
  parameters: Record<string, string> = {},
) {
  const item = consoleRoutes.find(({ id }) => id === routeId);
  if (!item) return undefined;
  return item.path.replace(/:([^/]+)/g, (_, name: string) => {
    const definition = item.entityParameters?.find(
      (candidate) => candidate.name === name,
    );
    if (!definition || parameters[name] === undefined)
      throw new Error(`Missing safe route parameter: ${name}`);
    return definition.encode(parameters[name]);
  });
}
const escapeRegex = (value: string) =>
  value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
export function matchRoute(
  pattern: string,
  pathname: string,
): Record<string, string> | null {
  const names: string[] = [];
  const source = pattern
    .split("/")
    .map((part) =>
      part.startsWith(":")
        ? (names.push(part.slice(1)), "([^/]+)")
        : escapeRegex(part),
    )
    .join("/");
  const match = new RegExp(`^${source}/?$`).exec(pathname);
  if (!match) return null;
  try {
    return Object.fromEntries(
      names.map((name, index) => [name, decodeURIComponent(match[index + 1])]),
    );
  } catch {
    return null;
  }
}
export function breadcrumbsForPath(pathname: string) {
  const current = routeForPath(pathname);
  if (!current) return [];
  const chain: ConsoleRoute[] = [];
  let item: ConsoleRoute | undefined = current;
  while (item) {
    chain.unshift(item);
    item = item.parentId
      ? consoleRoutes.find((candidate) => candidate.id === item!.parentId)
      : undefined;
  }
  const params = matchRoute(current.path, pathname) ?? {};
  return chain.map((entry) => ({
    id: entry.id,
    path: entry === current ? pathname : entry.path,
    label:
      entry === current && entry.entityParameters?.length
        ? params[entry.entityParameters[0].name] || entry.breadcrumb
        : entry.breadcrumb,
  }));
}
export function titleForPath(pathname: string) {
  const current = routeForPath(pathname);
  if (!current) return "DataObs — Page not found";
  const params = matchRoute(current.path, pathname) ?? {};
  const entityParam = current.entityParameters?.[0];
  const label = entityParam
    ? params[entityParam.name] || current.name
    : current.name;
  return `DataObs — ${current.name}${entityParam && label !== current.name ? ` ${label}` : ""}`;
}
