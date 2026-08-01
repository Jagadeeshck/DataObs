import { Route, Routes } from "react-router-dom";
import { QualityConsole } from "./QualityConsole";
import { Monitor360 } from "./Monitor360";
import { MonitorAuthoring } from "./MonitorAuthoring";
import { MonitorInventory } from "./MonitorInventory";
export default function QualityRoutes() {
  return (
    <Routes>
      <Route index element={<QualityConsole />} />
      <Route path="monitors" element={<MonitorInventory />} />
      <Route path="monitors/new" element={<MonitorAuthoring />} />
      <Route path="monitors/:monitorId" element={<Monitor360 />} />
    </Routes>
  );
}
