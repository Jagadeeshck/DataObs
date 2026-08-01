export type CapabilityAvailability =
  | "available"
  | "preview"
  | "not_configured"
  | "planned"
  | "unavailable";
export type NavigationGroup = "Overview" | "Observe" | "Respond" | "Configure";
export type RouteLoaderId =
  | "commandCenter"
  | "flow"
  | "assets"
  | "asset"
  | "quality"
  | "monitors"
  | "monitorNew"
  | "monitor"
  | "jobs"
  | "job"
  | "run"
  | "runCompare"
  | "lineage"
  | "pathways"
  | "pathway"
  | "streams"
  | "cluster"
  | "topic"
  | "consumerGroup"
  | "connector"
  | "schema"
  | "dataProducts"
  | "dataProduct"
  | "incidents"
  | "incident"
  | "integrations"
  | "integration"
  | "onboarding";

export interface ConsoleRoute {
  id: string;
  path: string;
  name: string;
  navigationLabel: string;
  group: NavigationGroup;
  icon: string;
  permission?: string;
  owner: `team-${0 | 1 | 2 | 3 | 4 | 5 | 6}`;
  implementation: CapabilityAvailability;
  navigation: boolean;
  hiddenButRoutable?: boolean;
  featureFlag?: string;
  parentId?: string;
  breadcrumb: string;
  title: string;
  dynamicLabel?: string;
  suspenseLabel: string;
  loader: RouteLoaderId;
}

const route = (value: ConsoleRoute) => value;
export const consoleRoutes: readonly ConsoleRoute[] = [
  route({
    id: "command-center",
    path: "/",
    name: "Command Center",
    navigationLabel: "Command Center",
    group: "Overview",
    icon: "⌁",
    owner: "team-5",
    implementation: "available",
    navigation: true,
    breadcrumb: "Command Center",
    title: "Command Center",
    suspenseLabel: "Loading Command Center…",
    loader: "commandCenter",
  }),
  route({
    id: "flow",
    path: "/flow",
    name: "Data Flow",
    navigationLabel: "Data Flow",
    group: "Overview",
    icon: "⌘",
    owner: "team-5",
    implementation: "available",
    navigation: true,
    breadcrumb: "Data Flow",
    title: "Data Flow",
    suspenseLabel: "Loading Data Flow…",
    loader: "flow",
  }),
  route({
    id: "assets",
    path: "/assets",
    name: "Assets",
    navigationLabel: "Assets",
    group: "Observe",
    icon: "◇",
    owner: "team-2",
    implementation: "available",
    navigation: true,
    breadcrumb: "Assets",
    title: "Assets",
    suspenseLabel: "Loading Assets…",
    loader: "assets",
  }),
  route({
    id: "asset",
    path: "/assets/:assetId",
    name: "Asset",
    navigationLabel: "Asset",
    group: "Observe",
    icon: "◇",
    owner: "team-2",
    implementation: "available",
    navigation: false,
    hiddenButRoutable: true,
    parentId: "assets",
    breadcrumb: "Asset",
    dynamicLabel: "assetId",
    title: "Asset",
    suspenseLabel: "Loading asset…",
    loader: "asset",
  }),
  route({
    id: "quality",
    path: "/quality",
    name: "Data Quality",
    navigationLabel: "Data Quality",
    group: "Observe",
    icon: "✓",
    permission: "quality:read",
    owner: "team-2",
    implementation: "available",
    navigation: true,
    breadcrumb: "Data Quality",
    title: "Data Quality",
    suspenseLabel: "Loading Data Quality…",
    loader: "quality",
  }),
  route({
    id: "quality-monitors",
    path: "/quality/monitors",
    name: "Monitor Inventory",
    navigationLabel: "Monitors",
    group: "Observe",
    icon: "✓",
    permission: "quality:read",
    owner: "team-2",
    implementation: "available",
    navigation: false,
    parentId: "quality",
    breadcrumb: "Monitors",
    title: "Monitor Inventory",
    suspenseLabel: "Loading monitors…",
    loader: "monitors",
  }),
  route({
    id: "quality-monitor-new",
    path: "/quality/monitors/new",
    name: "New Monitor",
    navigationLabel: "New monitor",
    group: "Observe",
    icon: "✓",
    permission: "quality:write",
    owner: "team-2",
    implementation: "preview",
    navigation: false,
    hiddenButRoutable: true,
    parentId: "quality-monitors",
    breadcrumb: "New",
    title: "New Monitor",
    suspenseLabel: "Loading monitor authoring…",
    loader: "monitorNew",
  }),
  route({
    id: "quality-monitor",
    path: "/quality/monitors/:monitorId",
    name: "Monitor",
    navigationLabel: "Monitor",
    group: "Observe",
    icon: "✓",
    permission: "quality:read",
    owner: "team-2",
    implementation: "available",
    navigation: false,
    hiddenButRoutable: true,
    parentId: "quality-monitors",
    breadcrumb: "Monitor",
    dynamicLabel: "monitorId",
    title: "Monitor",
    suspenseLabel: "Loading monitor…",
    loader: "monitor",
  }),
  route({
    id: "jobs",
    path: "/jobs",
    name: "Jobs",
    navigationLabel: "Jobs",
    group: "Observe",
    icon: "▤",
    permission: "jobs:read",
    owner: "team-2",
    implementation: "available",
    navigation: true,
    breadcrumb: "Jobs",
    title: "Jobs",
    suspenseLabel: "Loading jobs…",
    loader: "jobs",
  }),
  route({
    id: "job",
    path: "/jobs/:jobId",
    name: "Job",
    navigationLabel: "Job",
    group: "Observe",
    icon: "▤",
    permission: "jobs:read",
    owner: "team-2",
    implementation: "available",
    navigation: false,
    hiddenButRoutable: true,
    parentId: "jobs",
    breadcrumb: "Job",
    dynamicLabel: "jobId",
    title: "Job",
    suspenseLabel: "Loading job…",
    loader: "job",
  }),
  route({
    id: "run-compare",
    path: "/runs/compare",
    name: "Run Comparison",
    navigationLabel: "Run comparison",
    group: "Observe",
    icon: "▤",
    permission: "jobs:read",
    owner: "team-2",
    implementation: "available",
    navigation: false,
    hiddenButRoutable: true,
    parentId: "jobs",
    breadcrumb: "Compare runs",
    title: "Run Comparison",
    suspenseLabel: "Loading run comparison…",
    loader: "runCompare",
  }),
  route({
    id: "run",
    path: "/runs/:runId",
    name: "Run",
    navigationLabel: "Run",
    group: "Observe",
    icon: "▤",
    permission: "jobs:read",
    owner: "team-2",
    implementation: "available",
    navigation: false,
    hiddenButRoutable: true,
    parentId: "jobs",
    breadcrumb: "Run",
    dynamicLabel: "runId",
    title: "Run",
    suspenseLabel: "Loading run…",
    loader: "run",
  }),
  route({
    id: "lineage",
    path: "/lineage",
    name: "Lineage",
    navigationLabel: "Lineage",
    group: "Observe",
    icon: "↝",
    permission: "lineage:read",
    owner: "team-2",
    implementation: "available",
    navigation: true,
    breadcrumb: "Lineage",
    title: "Lineage",
    suspenseLabel: "Loading Lineage…",
    loader: "lineage",
  }),
  route({
    id: "pathways",
    path: "/pathways",
    name: "Pathways",
    navigationLabel: "Pathways",
    group: "Observe",
    icon: "⇄",
    permission: "pathways:read",
    owner: "team-1",
    implementation: "available",
    navigation: true,
    breadcrumb: "Pathways",
    title: "Pathways",
    suspenseLabel: "Loading pathways…",
    loader: "pathways",
  }),
  route({
    id: "pathway",
    path: "/pathways/:pathwayId",
    name: "Pathway",
    navigationLabel: "Pathway",
    group: "Observe",
    icon: "⇄",
    permission: "pathways:read",
    owner: "team-1",
    implementation: "available",
    navigation: false,
    hiddenButRoutable: true,
    parentId: "pathways",
    breadcrumb: "Pathway",
    dynamicLabel: "pathwayId",
    title: "Pathway",
    suspenseLabel: "Loading pathway…",
    loader: "pathway",
  }),
  route({
    id: "streams",
    path: "/streams",
    name: "Streams",
    navigationLabel: "Streams",
    group: "Observe",
    icon: "≋",
    permission: "streams:read",
    owner: "team-1",
    implementation: "available",
    navigation: true,
    breadcrumb: "Streams",
    title: "Streams",
    suspenseLabel: "Loading streams…",
    loader: "streams",
  }),
  ...(
    [
      [
        "cluster",
        "/streams/clusters/:clusterId",
        "Kafka cluster",
        "clusterId",
        "cluster",
      ],
      [
        "topic",
        "/streams/topics/:streamId",
        "Kafka topic",
        "streamId",
        "topic",
      ],
      [
        "consumer-group",
        "/streams/consumer-groups/:groupId",
        "Consumer group",
        "groupId",
        "consumerGroup",
      ],
      [
        "connector",
        "/streams/connectors/:connectorId",
        "Connector",
        "connectorId",
        "connector",
      ],
      [
        "schema",
        "/streams/schemas/:subjectId",
        "Schema subject",
        "subjectId",
        "schema",
      ],
    ] as const
  ).map(([id, path, name, param, loader]) =>
    route({
      id: `streams-${id}`,
      path,
      name,
      navigationLabel: name,
      group: "Observe",
      icon: "≋",
      permission: "streams:read",
      owner: "team-1",
      implementation: "available",
      navigation: false,
      hiddenButRoutable: true,
      parentId: "streams",
      breadcrumb: name,
      dynamicLabel: param,
      title: name,
      suspenseLabel: `Loading ${name.toLowerCase()}…`,
      loader,
    }),
  ),
  route({
    id: "data-products",
    path: "/data-products",
    name: "Data Products",
    navigationLabel: "Data Products",
    group: "Observe",
    icon: "▣",
    permission: "data-products:read",
    owner: "team-2",
    implementation: "available",
    navigation: true,
    breadcrumb: "Data Products",
    title: "Data Products",
    suspenseLabel: "Loading data products…",
    loader: "dataProducts",
  }),
  route({
    id: "data-product",
    path: "/data-products/:productId",
    name: "Data Product",
    navigationLabel: "Data Product",
    group: "Observe",
    icon: "▣",
    permission: "data-products:read",
    owner: "team-2",
    implementation: "available",
    navigation: false,
    hiddenButRoutable: true,
    parentId: "data-products",
    breadcrumb: "Data Product",
    dynamicLabel: "productId",
    title: "Data Product",
    suspenseLabel: "Loading data product…",
    loader: "dataProduct",
  }),
  route({
    id: "incidents",
    path: "/incidents",
    name: "Incident Inbox",
    navigationLabel: "Incidents",
    group: "Respond",
    icon: "!",
    permission: "incidents:read",
    owner: "team-3",
    implementation: "available",
    navigation: true,
    breadcrumb: "Incidents",
    title: "Incident Inbox",
    suspenseLabel: "Loading incidents…",
    loader: "incidents",
  }),
  route({
    id: "incident",
    path: "/incidents/:incidentId",
    name: "Incident",
    navigationLabel: "Incident",
    group: "Respond",
    icon: "!",
    permission: "incidents:read",
    owner: "team-3",
    implementation: "available",
    navigation: false,
    hiddenButRoutable: true,
    parentId: "incidents",
    breadcrumb: "Incident",
    dynamicLabel: "incidentId",
    title: "Incident",
    suspenseLabel: "Loading incident…",
    loader: "incident",
  }),
  route({
    id: "integrations",
    path: "/integrations",
    name: "Integrations",
    navigationLabel: "Integrations",
    group: "Configure",
    icon: "+",
    permission: "integrations:read",
    owner: "team-5",
    implementation: "available",
    navigation: true,
    breadcrumb: "Integrations",
    title: "Integrations",
    suspenseLabel: "Loading integrations…",
    loader: "integrations",
  }),
  route({
    id: "integration",
    path: "/integrations/:integrationId",
    name: "Integration",
    navigationLabel: "Integration",
    group: "Configure",
    icon: "+",
    permission: "integrations:read",
    owner: "team-5",
    implementation: "available",
    navigation: false,
    hiddenButRoutable: true,
    parentId: "integrations",
    breadcrumb: "Integration",
    dynamicLabel: "integrationId",
    title: "Integration",
    suspenseLabel: "Loading integration…",
    loader: "integration",
  }),
  route({
    id: "onboarding",
    path: "/onboarding",
    name: "Get started",
    navigationLabel: "Get started",
    group: "Configure",
    icon: "→",
    owner: "team-5",
    implementation: "available",
    navigation: true,
    breadcrumb: "Onboarding",
    title: "Onboarding",
    suspenseLabel: "Loading onboarding…",
    loader: "onboarding",
  }),
] as const;

export type RuntimeCapabilityState = CapabilityAvailability | "unknown";
export interface EffectiveRouteState {
  implementation: CapabilityAvailability;
  authorised: boolean;
  configuration: RuntimeCapabilityState;
  actionable: boolean;
}
export function resolveRouteState(
  route: ConsoleRoute,
  permissions: readonly string[],
  capabilities?: Record<string, RuntimeCapabilityState>,
): EffectiveRouteState {
  const authorised =
    !route.permission || permissions.includes(route.permission);
  const configuration =
    capabilities?.[route.id] ??
    capabilities?.[route.parentId ?? ""] ??
    "unknown";
  return {
    implementation: route.implementation,
    authorised,
    configuration,
    actionable:
      authorised &&
      ["available", "preview"].includes(route.implementation) &&
      (configuration === "available" || configuration === "preview"),
  };
}
export function visibleRoutes(permissions: readonly string[]) {
  return consoleRoutes.filter(
    (item) =>
      item.navigation && resolveRouteState(item, permissions).authorised,
  );
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
export function routeForPath(pathname: string) {
  return consoleRoutes.find((item) => matchRoute(item.path, pathname));
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
      entry === current && entry.dynamicLabel
        ? params[entry.dynamicLabel] || entry.breadcrumb
        : entry.breadcrumb,
  }));
}
export function titleForPath(pathname: string) {
  const current = routeForPath(pathname);
  if (!current) return "DataObs — Page not found";
  const params = matchRoute(current.path, pathname) ?? {};
  const label = current.dynamicLabel
    ? params[current.dynamicLabel] || current.title
    : current.title;
  return `DataObs — ${current.title}${current.dynamicLabel && label !== current.title ? ` ${label}` : ""}`;
}
