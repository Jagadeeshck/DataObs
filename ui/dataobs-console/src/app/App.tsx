import { lazy, Suspense, type ComponentType } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AppShell } from "../layouts/AppShell";
import { ProductContextProvider, useProductContext } from "../state/context";
import { Callback, Login, Logout, Unauthorised } from "../auth/AuthPages";
import { NotFound, RouteBoundary } from "./RouteStates";
import { consoleRoutes, type ConsoleRoute, type RouteLoaderId } from "./routes";

type Loader = () => Promise<{ default: ComponentType }>;
const loaders: Record<RouteLoaderId, Loader> = {
  commandCenter: () =>
    import("../features/command-center/CommandCenter").then((m) => ({
      default: m.CommandCenter,
    })),
  flow: () =>
    import("../features/flow-map/FlowMap").then((m) => ({
      default: m.FlowMap,
    })),
  assets: () =>
    import("../features/assets/AssetCatalog").then((m) => ({
      default: m.AssetCatalog,
    })),
  asset: () =>
    import("../features/assets/Asset360").then((m) => ({
      default: m.Asset360,
    })),
  quality: () =>
    import("../features/quality/QualityOverview").then((m) => ({
      default: m.QualityOverview,
    })),
  monitors: () =>
    import("../features/quality/MonitorInventory").then((m) => ({
      default: m.MonitorInventory,
    })),
  monitorNew: () =>
    import("../features/quality/MonitorAuthoring").then((m) => ({
      default: m.MonitorAuthoring,
    })),
  monitor: () =>
    import("../features/quality/Monitor360").then((m) => ({
      default: m.Monitor360,
    })),
  jobs: () =>
    import("../features/jobs/JobRunExplorer").then((m) => ({
      default: m.JobsInventory,
    })),
  job: () =>
    import("../features/jobs/JobRunExplorer").then((m) => ({
      default: m.Job360,
    })),
  run: () =>
    import("../features/jobs/JobRunExplorer").then((m) => ({
      default: m.Run360,
    })),
  runCompare: () =>
    import("../features/jobs/JobRunExplorer").then((m) => ({
      default: m.RunComparison,
    })),
  lineage: () =>
    import("../features/lineage/LineageExplorer").then((m) => ({
      default: m.LineageExplorer,
    })),
  pathways: () =>
    import("../features/pathways/PathwayExplorer").then((m) => ({
      default: m.PathwayExplorer,
    })),
  pathway: () =>
    import("../features/pathways/PathwayExplorer").then((m) => ({
      default: m.PathwayExplorer,
    })),
  streams: () =>
    import("../features/streams/StreamsInventory").then((m) => ({
      default: m.StreamsInventory,
    })),
  cluster: () =>
    import("../features/streams/Cluster360").then((m) => ({
      default: m.Cluster360,
    })),
  topic: () =>
    import("../features/streams/Stream360").then((m) => ({
      default: () => <m.Stream360 kind="topic" />,
    })),
  consumerGroup: () =>
    import("../features/streams/Stream360").then((m) => ({
      default: () => <m.Stream360 kind="group" />,
    })),
  connector: () =>
    import("../features/streams/Connector360").then((m) => ({
      default: m.Connector360,
    })),
  schema: () =>
    import("../features/streams/Schema360").then((m) => ({
      default: m.Schema360,
    })),
  dataProducts: () =>
    import("../features/data-products/DataProductList").then((m) => ({
      default: m.DataProductList,
    })),
  dataProduct: () =>
    import("../features/data-products/DataProduct360").then((m) => ({
      default: m.DataProduct360,
    })),
  incidents: () =>
    import("../features/incidents/IncidentInbox").then((m) => ({
      default: m.IncidentInbox,
    })),
  incident: () =>
    import("../features/incidents/IncidentDetail").then((m) => ({
      default: m.IncidentDetail,
    })),
  integrations: () =>
    import("../features/integrations/Integrations").then((m) => ({
      default: m.Integrations,
    })),
  integration: () =>
    import("../features/integrations/Integrations").then((m) => ({
      default: m.IntegrationDetail,
    })),
  onboarding: () =>
    import("../features/onboarding/Onboarding").then((m) => ({
      default: m.Onboarding,
    })),
};
export const implementedLoaderIds = Object.freeze(
  Object.keys(loaders) as RouteLoaderId[],
);
const components = Object.fromEntries(
  implementedLoaderIds.map((id) => [id, lazy(loaders[id])]),
) as unknown as Record<RouteLoaderId, ComponentType>;
function RouteImplementation({ route }: { route: ConsoleRoute }) {
  const { identity } = useProductContext();
  if (route.permission && !identity?.permissions.includes(route.permission))
    return <Navigate to="/unauthorised" replace />;
  const Component = components[route.loader];
  return (
    <RouteBoundary key={route.id}>
      <Suspense
        fallback={
          <p className="route-loading" role="status">
            {route.suspenseLabel}
          </p>
        }
      >
        <Component />
      </Suspense>
    </RouteBoundary>
  );
}
export function App() {
  return (
    <ProductContextProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/auth/callback" element={<Callback />} />
          <Route path="/logout" element={<Logout />} />
          <Route path="/unauthorised" element={<Unauthorised />} />
          <Route element={<AppShell />}>
            {consoleRoutes.map((route) => (
              <Route
                key={route.id}
                index={route.path === "/"}
                path={route.path === "/" ? undefined : route.path.slice(1)}
                element={<RouteImplementation route={route} />}
              />
            ))}
            <Route path="*" element={<NotFound />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ProductContextProvider>
  );
}
