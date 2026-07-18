import { BrowserRouter, Route, Routes } from "react-router-dom";
import { AppShell } from "../layouts/AppShell";
import { CommandCenter } from "../features/command-center/CommandCenter";
import { FlowMap } from "../features/flow-map/FlowMap";
import { IncidentDetail } from "../features/incidents/IncidentDetail";
import { ProductContextProvider } from "../state/context";
export function App() {
  return (
    <ProductContextProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<AppShell />}>
            <Route index element={<CommandCenter />} />
            <Route path="flow" element={<FlowMap />} />
            <Route path="incidents/:incidentId" element={<IncidentDetail />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ProductContextProvider>
  );
}
