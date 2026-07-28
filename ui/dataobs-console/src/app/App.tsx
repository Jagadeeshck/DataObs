import { lazy, Suspense } from "react";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AppShell } from "../layouts/AppShell";
import { CommandCenter } from "../features/command-center/CommandCenter";
import { FlowMap } from "../features/flow-map/FlowMap";
import { IncidentDetail } from "../features/incidents/IncidentDetail";
import { ProductContextProvider } from "../state/context";
import { AssetCatalog } from "../features/assets/AssetCatalog";
import { Asset360 } from "../features/assets/Asset360";
import { PathwayExplorer } from "../features/pathways/PathwayExplorer";
import { Callback, Login, Logout, Unauthorised } from "../auth/AuthPages";
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
            <Route element={<AppShell />}>
              <Route index element={<CommandCenter />} />
              <Route path="flow" element={<FlowMap />} />
              <Route path="assets" element={<AssetCatalog />} />
              <Route path="assets/:assetId" element={<Asset360 />} />
              <Route path="pathways" element={<PathwayExplorer />} />
              <Route path="pathways/:pathwayId" element={<PathwayExplorer />} />
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
                element={<Stream360 kind="cluster" />}
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
                element={<Stream360 kind="connector" />}
              />
              <Route
                path="streams/schemas/:subjectId"
                element={<Stream360 kind="schema" />}
              />
            </Route>
          </Routes>
        </Suspense>
      </BrowserRouter>
    </ProductContextProvider>
  );
}
