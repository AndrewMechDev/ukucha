import { useState, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";

type SideNavProps = {
  collapsed: boolean;
  onToggle: () => void;
};

type NavItem = {
  id: "fleet" | "alerts" | "settings";
  label: string;
  icon: ReactNode;
  badge?: number;
};

const icons = {
  fleet: (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M5 9.5 12 6l7 3.5v7L12 20l-7-3.5v-7Z" />
      <path d="m5 9.5 7 3.5 7-3.5M12 13v7M8.5 6.2 12 8l3.5-1.8" />
    </svg>
  ),
  alerts: (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M18 9a6 6 0 0 0-12 0c0 7-3 7-3 8h18c0-1-3-1-3-8Z" />
      <path d="M10 21h4" />
    </svg>
  ),
  settings: (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-2.8 2.8-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.6v.2h-4V21a1.7 1.7 0 0 0-1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1L4.2 17l.1-.1a1.7 1.7 0 0 0 .3-1.9A1.7 1.7 0 0 0 3 14H2.8v-4H3a1.7 1.7 0 0 0 1.6-1 1.7 1.7 0 0 0-.3-1.9L4.2 7 7 4.2l.1.1A1.7 1.7 0 0 0 9 4.6a1.7 1.7 0 0 0 1-1.6v-.2h4V3a1.7 1.7 0 0 0 1 1.6 1.7 1.7 0 0 0 1.9-.3l.1-.1L19.8 7l-.1.1a1.7 1.7 0 0 0-.3 1.9 1.7 1.7 0 0 0 1.6 1h.2v4H21a1.7 1.7 0 0 0-1.6 1Z" />
    </svg>
  ),
};

const navItems: NavItem[] = [
  { id: "fleet", label: "Flota", icon: icons.fleet },
  { id: "alerts", label: "Alertas", icon: icons.alerts, badge: 3 },
  { id: "settings", label: "Ajustes", icon: icons.settings },
];

function Brand({ compact = false, onClick }: { compact?: boolean; onClick: () => void }) {
  return (
    <button
      className={`brand${compact ? " brand--compact" : ""}`}
      type="button"
      onClick={onClick}
      aria-label={compact ? "Expandir navegación" : "Colapsar navegación"}
      aria-expanded={!compact}
    >
      <span className="brand__mark" aria-hidden="true">
        <span />
      </span>
      {!compact && <span className="brand__wordmark">UKUCHA</span>}
      <span className="brand__chevron" aria-hidden="true">
        <svg viewBox="0 0 24 24">
          <path d={compact ? "m9 6 6 6-6 6" : "m15 6-6 6 6 6"} />
        </svg>
      </span>
    </button>
  );
}

export default function SideNav({ collapsed, onToggle }: SideNavProps) {
  const navigate = useNavigate();
  const [activeItem, setActiveItem] = useState<NavItem["id"]>("fleet");

  return (
    <>
      <aside className={`side-nav${collapsed ? " side-nav--collapsed" : ""}`}>
        <header className="side-nav__header">
          <Brand compact={collapsed} onClick={onToggle} />
        </header>

        <nav className="side-nav__items" aria-label="Navegación principal">
          {navItems.map((item) => (
            <button
              className={`nav-item${activeItem === item.id ? " nav-item--active" : ""}`}
              type="button"
              key={item.id}
              onClick={() => {
                setActiveItem(item.id);
                if (item.id === "fleet") navigate("/");
                if (item.id === "alerts") navigate("/alerts");
              }}
              aria-current={activeItem === item.id ? "page" : undefined}
              aria-label={collapsed ? item.label : undefined}
            >
              <span className="nav-item__icon">{item.icon}</span>
              {!collapsed && <span className="nav-item__label">{item.label}</span>}
              {item.badge !== undefined && (
                <span className="nav-item__badge" aria-label={`${item.badge} alertas críticas sin reconocer`}>
                  {item.badge}
                </span>
              )}
              {collapsed && <span className="glass-tooltip">{item.label}</span>}
            </button>
          ))}
        </nav>

        <footer className="side-nav__footer">
          <span className="system-status__dot" aria-hidden="true" />
          {!collapsed && <span className="system-status__label">N unidades activas</span>}
          {collapsed && <span className="glass-tooltip">N unidades activas</span>}
        </footer>
      </aside>

      <nav className="bottom-nav" aria-label="Navegación principal">
        {navItems.map((item) => (
          <button
            className={`bottom-nav__item${activeItem === item.id ? " bottom-nav__item--active" : ""}`}
            type="button"
            key={item.id}
            onClick={() => setActiveItem(item.id)}
            aria-current={activeItem === item.id ? "page" : undefined}
          >
            <span className="nav-item__icon">{item.icon}</span>
            <span>{item.label}</span>
            {item.badge !== undefined && <span className="bottom-nav__badge">{item.badge}</span>}
          </button>
        ))}
      </nav>
    </>
  );
}
