export type CapabilityAvailability =
  | "available"
  | "preview"
  | "not_configured"
  | "planned"
  | "unavailable";
export type NavigationGroup = "Overview" | "Observe" | "Respond" | "Configure";

export interface ConsoleRoute {
  id: string;
  path: string;
  name: string;
  group: NavigationGroup;
  icon: string;
  permission?: string;
  owner: `team-${0 | 1 | 2 | 3 | 4 | 5}`;
  availability: CapabilityAvailability;
  breadcrumb: string;
  navigation: boolean;
  featureFlag?: string;
  children?: string[];
}

/** Product discovery metadata only; React elements remain lazy imports in App. */
export const consoleRoutes: readonly ConsoleRoute[] = [
  {
    id: "command-center",
    path: "/",
    name: "Command Center",
    group: "Overview",
    icon: "⌁",
    owner: "team-5",
    availability: "available",
    breadcrumb: "Command Center",
    navigation: true,
  },
  {
    id: "flow",
    path: "/flow",
    name: "Data Flow",
    group: "Overview",
    icon: "⌘",
    owner: "team-5",
    availability: "available",
    breadcrumb: "Data Flow",
    navigation: true,
  },
  {
    id: "pathways",
    path: "/pathways",
    name: "Pathways",
    group: "Observe",
    icon: "⇄",
    owner: "team-1",
    availability: "available",
    breadcrumb: "Pathways",
    navigation: true,
    children: ["/pathways/:pathwayId"],
  },
  {
    id: "assets",
    path: "/assets",
    name: "Assets",
    group: "Observe",
    icon: "◇",
    owner: "team-2",
    availability: "available",
    breadcrumb: "Assets",
    navigation: true,
    children: ["/assets/:assetId"],
  },
  {
    id: "streams",
    path: "/streams",
    name: "Streams",
    group: "Observe",
    icon: "≋",
    owner: "team-1",
    availability: "available",
    breadcrumb: "Streams",
    navigation: true,
    children: [
      "/streams/clusters/:clusterId",
      "/streams/topics/:streamId",
      "/streams/consumer-groups/:groupId",
      "/streams/connectors/:connectorId",
      "/streams/schemas/:subjectId",
    ],
  },
  {
    id: "data-products",
    path: "/data-products",
    name: "Data Products",
    group: "Observe",
    icon: "▣",
    owner: "team-2",
    availability: "available",
    breadcrumb: "Data Products",
    navigation: true,
    children: ["/data-products/:productId"],
  },
  {
    id: "jobs",
    path: "/jobs",
    name: "Jobs",
    group: "Observe",
    icon: "▤",
    owner: "team-2",
    availability: "available",
    breadcrumb: "Jobs",
    navigation: true,
    children: ["/jobs/:jobId", "/runs/:runId", "/runs/compare"],
  },
  {
    id: "lineage",
    path: "/lineage",
    name: "Lineage",
    group: "Observe",
    icon: "↝",
    owner: "team-2",
    availability: "available",
    breadcrumb: "Lineage",
    navigation: true,
  },
  {
    id: "quality",
    path: "/quality",
    name: "Data Quality",
    group: "Observe",
    icon: "✓",
    owner: "team-4",
    availability: "available",
    breadcrumb: "Data Quality",
    navigation: true,
    children: [
      "/quality/monitors",
      "/quality/monitors/new",
      "/quality/monitors/:monitorId",
    ],
  },
  {
    id: "incidents",
    path: "/incidents",
    name: "Incidents",
    group: "Respond",
    icon: "!",
    permission: "incidents:read",
    owner: "team-3",
    availability: "not_configured",
    breadcrumb: "Incidents",
    navigation: true,
    children: ["/incidents/:incidentId"],
  },
  {
    id: "integrations",
    path: "/integrations",
    name: "Integrations",
    group: "Configure",
    icon: "+",
    permission: "integrations:read",
    owner: "team-5",
    availability: "available",
    breadcrumb: "Integrations",
    navigation: true,
    children: ["/integrations/:integrationId"],
  },
  {
    id: "onboarding",
    path: "/onboarding",
    name: "Get started",
    group: "Configure",
    icon: "→",
    owner: "team-5",
    availability: "available",
    breadcrumb: "Onboarding",
    navigation: true,
  },
] as const;

export function visibleRoutes(permissions: readonly string[]) {
  return consoleRoutes.filter(
    (route) => !route.permission || permissions.includes(route.permission),
  );
}

const normalise = (value: string) =>
  value !== "/" && value.endsWith("/") ? value.slice(0, -1) : value;
const matches = (pattern: string, pathname: string) => {
  const expression = pattern.replace(/:[^/]+/g, "[^/]+");
  return new RegExp(`^${expression}$`).test(normalise(pathname));
};
export function routeForPath(pathname: string) {
  return consoleRoutes.find(
    (route) =>
      matches(route.path, pathname) ||
      route.children?.some((child) => matches(child, pathname)),
  );
}
