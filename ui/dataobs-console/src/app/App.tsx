import { lazy, Suspense, type ComponentType } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AppShell } from "../layouts/AppShell";
import { ProductContextProvider } from "../state/context";
<<<<<<< HEAD
import { AssetCatalog } from "../features/assets/AssetCatalog";
import { Asset360 } from "../features/assets/Asset360";
import { PathwayExplorer } from "../features/pathways/PathwayExplorer";
import { Callback, Login, Logout, Unauthorised } from "../auth/AuthPages";
import { NotFound, RouteError } from "./RouteStates";
import {
  Integrations,
  IntegrationDetail,
} from "../features/integrations/Integrations";
import { Onboarding } from "../features/onboarding/Onboarding";
import {
  Job360,
  JobsInventory,
  Run360,
  RunComparison,
} from "../features/jobs/JobRunExplorer";
import { LineageExplorer } from "../features/lineage/LineageExplorer";
const StreamsInventory = lazy(() =>
  import("../features/streams/StreamsInventory").then((m) => ({
    default: m.StreamsInventory,
  })),
);
const Stream360 = lazy(() =>
  import("../features/streams/Stream360").then((m) => ({
    default: m.Stream360,
  })),
);
const Connector360 = lazy(() =>
  import("../features/streams/Connector360").then((m) => ({
    default: m.Connector360,
  })),
);
const Schema360 = lazy(() =>
  import("../features/streams/Schema360").then((m) => ({
    default: m.Schema360,
  })),
);
const Cluster360 = lazy(() =>
  import("../features/streams/Cluster360").then((m) => ({
    default: m.Cluster360,
  })),
);
const DataProductList = lazy(() =>
  import("../features/data-products/DataProductList").then((m) => ({
    default: m.DataProductList,
  })),
);
const DataProduct360 = lazy(() =>
  import("../features/data-products/DataProduct360").then((m) => ({
    default: m.DataProduct360,
  })),
);
const QualityRoutes = lazy(() => import("../features/quality/QualityRoutes"));
=======
import { NotFound, RouteBoundary } from "./RouteStates";
import { consoleRoutes } from "./routes";

const lazyComponents = new Map<string, ComponentType>();
function componentFor(route: (typeof consoleRoutes)[number]) {
  let component = lazyComponents.get(route.id);
  if (!component) {
    component = lazy(route.loader);
    lazyComponents.set(route.id, component);
  }
  const Component = component;
  return (
    <RouteBoundary routeName={route.name}>
      <Suspense
        fallback={
          <p className="route-loading" role="status">
            Loading {route.name}…
          </p>
        }
      >
        <Component />
      </Suspense>
    </RouteBoundary>
  );
}

>>>>>>> origin/main
export function App() {
  const publicRoutes = consoleRoutes.filter((route) => !route.protected);
  const protectedRoutes = consoleRoutes.filter((route) => route.protected);
  return (
    <ProductContextProvider>
      <BrowserRouter>
        <Routes>
          {publicRoutes.map((route) => (
            <Route
              key={route.id}
              path={route.path}
              element={componentFor(route)}
            />
          ))}
          <Route element={<AppShell />}>
            {protectedRoutes.map((route) => (
              <Route
                key={route.id}
                path={route.path}
                element={componentFor(route)}
              />
<<<<<<< HEAD
              <Route path="onboarding" element={<Onboarding />} />
              <Route path="incidents" element={<IncidentInbox />} />
              <Route path="quality/*" element={<QualityRoutes />} />
              <Route
                path="incidents/:incidentId"
                element={<IncidentDetail />}
              />
              <Route path="streams" element={<StreamsInventory />} />
              <Route path="data-products" element={<DataProductList />} />
              <Route
                path="data-products/:productId"
                element={<DataProduct360 />}
              />
              <Route
                path="streams/clusters/:clusterId"
                element={<Cluster360 />}
              />
              <Route
                path="streams/topics/:streamId"
                element={<Stream360 kind="topic" />}
              />
              <Route
                path="streams/consumer-groups/:groupId"
                element={<Stream360 kind="group" />}
              />
              <Route
                path="streams/connectors/:connectorId"
                element={<Connector360 />}
              />
              <Route
                path="streams/schemas/:subjectId"
                element={<Schema360 />}
              />
              <Route path="*" element={<NotFound />} />
            </Route>
          </Routes>
        </Suspense>
=======
            ))}
            <Route path="*" element={<NotFound />} />
          </Route>
        </Routes>
>>>>>>> origin/main
      </BrowserRouter>
    </ProductContextProvider>
  );
}
