import { useEffect, useState } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import SideNav from "./SideNav";
import Alerts from "../pages/Alerts";
import Settings from "../pages/Settings";

export default function Layout() {
  const [collapsed, setCollapsed] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const panel = new URLSearchParams(location.search).get("panel");

  useEffect(() => {
    const savedTheme = localStorage.getItem("theme");
    if (savedTheme === "light") {
      document.documentElement.setAttribute("data-theme", "light");
    } else {
      document.documentElement.setAttribute("data-theme", "dark");
    }
  }, []);

  const closePanel = () => {
    navigate({ pathname: location.pathname, search: "" });
  };

  return (
    <div className={`app-shell${collapsed ? " app-shell--collapsed" : ""}`}>
      <SideNav collapsed={collapsed} onToggle={() => setCollapsed((value) => !value)} />
      <main className="main-viewport">
        <Outlet />
      </main>
      {panel === "alerts" && <Alerts onClose={closePanel} />}
      {panel === "settings" && <Settings onClose={closePanel} />}
    </div>
  );
}
