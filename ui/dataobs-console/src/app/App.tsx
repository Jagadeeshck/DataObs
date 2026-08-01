import { lazy, Suspense } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AppShell } from "../layouts/AppShell";
import { CommandCenter } from "../features/command-center/CommandCenter";
import { FlowMap } from "../features/flow-map/FlowMap";
import { IncidentDetail } from "../features/incidents/IncidentDetail";
import { IncidentInbox } from "../features/incidents/IncidentInbox";
import { ProductContextProvider } from "../state/context";
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
import { QualityOverview } from "../features/quality/QualityOverview";
import { MonitorInventory } from "../features/quality/MonitorInventory";
import { MonitorAuthoring } from "../features/quality/MonitorAuthoring";
import { Monitor360 } from "../features/quality/Monitor360";
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
export function App() {
  return (
    <ProductContextProvider>
      <BrowserRouter>
        <Suspense fallback={<p role="status">Loading Stream evidence…</p>}>
          <Routes>
            <Route path="login" element={<Login />} />
            <Route path="auth/callback" element={<Callback />} />
            <Route path="logout" element={<Logout />} />
            <Route path="unauthorised" element={<Unauthorised />} />
            <Route element={<AppShell />} errorElement={<RouteError />}>
              <Route index element={<CommandCenter />} />
              <Route path="flow" element={<FlowMap />} />
              <Route path="assets" element={<AssetCatalog />} />
              <Route path="assets/:assetId" element={<Asset360 />} />
              <Route path="pathways" element={<PathwayExplorer />} />
              <Route path="pathways/:pathwayId" element={<PathwayExplorer />} />
              <Route path="jobs" element={<JobsInventory />} />
              <Route path="jobs/:jobId" element={<Job360 />} />
              <Route path="runs/:runId" element={<Run360 />} />
              <Route path="runs/compare" element={<RunComparison />} />
              <Route path="lineage" element={<LineageExplorer />} />
              <Route path="integrations" element={<Integrations />} />
              <Route
                path="integrations/:integrationId"
                element={<IntegrationDetail />}
              />
              <Route path="onboarding" element={<Onboarding />} />
              <Route path="quality" element={<QualityOverview />} />
              <Route path="quality/monitors" element={<MonitorInventory />} />
              <Route
                path="quality/monitors/new"
                element={<MonitorAuthoring />}
              />
              <Route
                path="quality/monitors/:monitorId"
                element={<Monitor360 />}
              />
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
      </BrowserRouter>
    </ProductContextProvider>
  );
}
