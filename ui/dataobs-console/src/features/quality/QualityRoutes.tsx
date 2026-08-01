import { Route, Routes } from "react-router-dom";
import { QualityConsole } from "./QualityConsole";
import { Monitor360 } from "./Monitor360";
export default function QualityRoutes() {
  return (
    <Routes>
      <Route index element={<QualityConsole />} />
      <Route path="monitors/:monitorId" element={<Monitor360 />} />
    </Routes>
  );
}
