import { useState } from "react";
import { Outlet } from "react-router-dom";
import SideNav from "./SideNav";

export default function Layout() {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className={`app-shell${collapsed ? " app-shell--collapsed" : ""}`}>
      <SideNav collapsed={collapsed} onToggle={() => setCollapsed((value) => !value)} />
      <main className="main-viewport">
        <Outlet />
      </main>
    </div>
  );
}
