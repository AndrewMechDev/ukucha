import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { useLanguage } from "./LanguageContext";

type SideNavProps = {
  collapsed: boolean;
  onToggle: () => void;
};

type NavItem = {
  id: "fleet" | "alerts" | "settings";
  label: string;
  icon: string;
  route: string;
  badge?: number;
};

const navItems: NavItem[] = [
  { id: "fleet", label: "Flota", icon: "deployed_code", route: "/" },
  { id: "alerts", label: "Alertas", icon: "notifications", route: "/alerts", badge: 3 },
  { id: "settings", label: "Ajustes", icon: "settings", route: "/settings" },
];

const primaryItem = navItems[0];
const optionItems = navItems.slice(1);

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
        <span className="material-symbols-rounded">pest_control_rodent</span>
      </span>
      <span className="brand__copy">
        <span className="brand__wordmark">Ukucha</span>
        <span className="brand__subtitle">Sar Dashboard</span>
      </span>
      <span className="brand__chevron" aria-hidden="true">
        <span className="material-symbols-rounded">{compact ? "chevron_right" : "chevron_left"}</span>
      </span>
    </button>
  );
}

export default function SideNav({ collapsed, onToggle }: SideNavProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const { t, language } = useLanguage();
  const panel = new URLSearchParams(location.search).get("panel");
  const currentItem: NavItem["id"] = panel === "alerts"
    ? "alerts"
    : panel === "settings"
      ? "settings"
      : "fleet";
  const [requestedItem, setRequestedItem] = useState<NavItem["id"] | null>(null);
  const activeItem = requestedItem ?? currentItem;

  useEffect(() => {
    setRequestedItem(null);
  }, [location.pathname, location.search]);

  const selectItem = (item: NavItem) => {
    setRequestedItem(item.id);
    if (item.id === "fleet") {
      navigate({ pathname: "/", search: "" });
      return;
    }
    navigate({ pathname: location.pathname, search: `?panel=${item.id}` });
  };

  const getLabel = (item: NavItem) => {
    if (item.id === "fleet") return t("flota");
    if (item.id === "alerts") return t("alertas");
    if (item.id === "settings") return t("ajustes");
    return item.label;
  };

  return (
    <>
      <aside className={`side-nav${collapsed ? " side-nav--collapsed" : ""}`}>
        <header className="side-nav__header">
          <Brand compact={collapsed} onClick={onToggle} />
        </header>

        <nav className="side-nav__items" aria-label="Navegación principal">
          {[primaryItem].map((item) => (
            <button
              className={`nav-item${activeItem === item.id ? " nav-item--active" : ""}`}
              type="button"
              key={item.id}
              onClick={() => selectItem(item)}
              aria-current={activeItem === item.id ? "page" : undefined}
              aria-label={collapsed ? getLabel(item) : undefined}
            >
              <span className="nav-item__icon material-symbols-rounded" aria-hidden="true">{item.icon}</span>
              {!collapsed && <span className="nav-item__label">{getLabel(item)}</span>}
              {item.badge !== undefined && (
                <span className="nav-item__badge" aria-label={`${item.badge} ${t("alertas").toLowerCase()}`}>
                  {item.badge}
                </span>
              )}
              {collapsed && <span className="glass-tooltip">{getLabel(item)}</span>}
            </button>
          ))}
          {!collapsed && <span className="side-nav__group-label">{language === "English" ? "Options" : "Opciones"}</span>}
          {optionItems.map((item) => (
            <button
              className={`nav-item${activeItem === item.id ? " nav-item--active" : ""}`}
              type="button"
              key={item.id}
              onClick={() => selectItem(item)}
              aria-current={activeItem === item.id ? "page" : undefined}
              aria-label={collapsed ? getLabel(item) : undefined}
            >
              <span className="nav-item__icon material-symbols-rounded" aria-hidden="true">{item.icon}</span>
              {!collapsed && <span className="nav-item__label">{getLabel(item)}</span>}
              {item.badge !== undefined && (
                <span className="nav-item__badge" aria-label={`${item.badge} ${t("alertas").toLowerCase()}`}>
                  {item.badge}
                </span>
              )}
              {collapsed && <span className="glass-tooltip">{getLabel(item)}</span>}
            </button>
          ))}
        </nav>
      </aside>

      <nav className="bottom-nav" aria-label="Navegación principal">
        {navItems.map((item) => (
          <button
            className={`bottom-nav__item${activeItem === item.id ? " bottom-nav__item--active" : ""}`}
            type="button"
            key={item.id}
            onClick={() => selectItem(item)}
            aria-current={activeItem === item.id ? "page" : undefined}
          >
            <span className="nav-item__icon material-symbols-rounded" aria-hidden="true">{item.icon}</span>
            <span>{getLabel(item)}</span>
            {item.badge !== undefined && <span className="bottom-nav__badge">{item.badge}</span>}
          </button>
        ))}
      </nav>
    </>
  );
}
