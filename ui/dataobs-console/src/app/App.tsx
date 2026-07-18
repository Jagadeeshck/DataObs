import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AppShell } from "../layouts/AppShell";
import { CommandCenter } from "../features/command-center/CommandCenter";
import { FlowMap } from "../features/flow-map/FlowMap";
import { IncidentDetail } from "../features/incidents/IncidentDetail";
import { ProductContextProvider } from "../state/context";
import { AssetCatalog } from "../features/assets/AssetCatalog";
import { Asset360 } from "../features/assets/Asset360";
import { PathwayExplorer } from "../features/pathways/PathwayExplorer";
export function App() {
  return (
    <ProductContextProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<AppShell />}>
            <Route index element={<CommandCenter />} />
            <Route path="flow" element={<FlowMap />} />
            <Route path="assets" element={<AssetCatalog />} />
            <Route path="assets/:assetId" element={<Asset360 />} />
            <Route path="pathways" element={<PathwayExplorer />} />
            <Route path="pathways/:pathwayId" element={<PathwayExplorer />} />
            <Route path="incidents/:incidentId" element={<IncidentDetail />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ProductContextProvider>
  );
}
