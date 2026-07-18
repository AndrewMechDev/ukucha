import { BrowserRouter, Navigate, Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import Home from "./pages/Home";
import Timeline from "./pages/Timeline";
import UnitDashboard from "./pages/UnitDashboard";
import UnitSensors from "./pages/UnitSensors";
import Copilot from "./pages/Copilot";
import NotFound from "./pages/NotFound";
import { LanguageProvider } from "./components/LanguageContext";
import PwaUpdatePrompt from "./components/PwaUpdatePrompt";

export default function App() {
  return (
    <LanguageProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<Home />} />
            <Route path="timeline" element={<Timeline />} />
            <Route path="copilot" element={<Copilot />} />
            <Route path="alerts" element={<Navigate to="/?panel=alerts" replace />} />
            <Route path="settings" element={<Navigate to="/?panel=settings" replace />} />
            <Route path="unit/:unitId" element={<UnitDashboard />} />
            <Route path="unit/:unitId/sensors" element={<UnitSensors />} />
            <Route path="*" element={<NotFound />} />
          </Route>
        </Routes>
        <PwaUpdatePrompt />
      </BrowserRouter>
    </LanguageProvider>
  );
}
