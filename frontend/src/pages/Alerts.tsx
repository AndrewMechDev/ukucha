import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import PanelModal from "../components/PanelModal";
import { useNotifications, type AppNotification, type NotificationSeverity } from "../components/NotificationsContext";

type AlertFilter = "Todas" | "Pendientes" | "Reconocidas";

function relativeAge(isoTimestamp: string): string {
  const ms = Date.now() - new Date(isoTimestamp).getTime();
  if (!Number.isFinite(ms) || ms < 0) return "";
  const minutes = Math.floor(ms / 60000);
  if (minutes < 1) return "hace instantes";
  if (minutes < 60) return `hace ${minutes} min`;
  const hours = Math.floor(minutes / 60);
  return `hace ${hours} h`;
}

function formatClock(isoTimestamp: string): string {
  const date = new Date(isoTimestamp);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleTimeString("es-PE", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

const icons = {
  check: <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m5 12 4 4L19 6" /></svg>,
  close: <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18" /></svg>,
  filter: <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 6h16M7 12h10M10 18h4" /></svg>,
  detail: <span className="material-symbols-rounded" aria-hidden="true">open_in_full</span>,
};

function SeverityTag({ severity }: { severity: NotificationSeverity }) {
  return <span className={`alerts-status-tag alerts-status-tag--${severity} alerts-filter-chip`}>{severity === "critical" ? "Crítica" : "Advertencia"}</span>;
}

export function EmptyAlerts() {
  return <div className="alerts-empty"><span className="alerts-empty__badge"><i /> SEGURO</span><h2>Sin alertas activas — todo en orden</h2></div>;
}

function AlertModal({ alert, onBack, onAcknowledge, onViewUnit }: { alert: AppNotification; onBack: () => void; onAcknowledge: () => void; onViewUnit: () => void }) {
  return (
    <section className="alerts-detail-view" aria-labelledby="alert-modal-title">
      <header className="alerts-detail-header">
        <button className="alerts-detail-back" type="button" onClick={onBack}><span className="material-symbols-rounded">arrow_back</span><span>Alertas</span></button>
      </header>
      <div className="alerts-detail-heading"><p className="eyebrow">DETALLE DE ALERTA</p><h2 id="alert-modal-title">{alert.severity === "critical" ? "Alerta crítica" : "Alerta de precaución"}</h2></div>
      <div className={`alerts-modal__summary alerts-modal__summary--${alert.severity}`}>
        <SeverityTag severity={alert.severity} />
        <strong>{alert.unit} · {alert.zone}</strong>
        <p>{alert.description}{alert.count > 1 ? ` (+${alert.count - 1} más en el ultimo minuto)` : ""}</p>
        <time>{formatClock(alert.timestamp)} · {relativeAge(alert.timestamp)}</time>
      </div>
      <div className="alerts-modal__actions"><button className="alerts-secondary-button" type="button" onClick={onViewUnit}>Ver unidad</button>{!alert.acknowledged && <button className="alerts-primary-button" type="button" onClick={onAcknowledge}>Reconocer alerta</button>}</div>
    </section>
  );
}

function AlertRow({ alert, onOpen }: { alert: AppNotification; onOpen: () => void }) {
  return (
    <article className={`alert-row alert-row--${alert.severity}${alert.acknowledged ? " alert-row--acknowledged" : ""}`} onClick={onOpen}>
      <span><SeverityTag severity={alert.severity} /></span>
      <span className="alert-unit"><strong>{alert.unit}</strong><small>{alert.zone}</small></span>
      <span className="alert-description">{alert.description}{alert.count > 1 ? ` (x${alert.count})` : ""}</span>
      <time>{formatClock(alert.timestamp)}</time>
      <span className={`alert-state alert-state-chip${alert.acknowledged ? " alert-state-chip--acknowledged" : " alert-state-chip--pending"}`}>{alert.acknowledged ? <>{icons.check}<span>Reconocida</span></> : <span>Pendiente</span>}</span>
      <span className="alert-action"><button className="alert-detail-button" type="button" aria-label={`Ver detalle de alerta de ${alert.unit}`} onClick={(event) => { event.stopPropagation(); onOpen(); }}>{icons.detail}</button></span>
    </article>
  );
}

export default function Alerts({ onClose }: { onClose?: () => void }) {
  const navigate = useNavigate();
  const { notifications, acknowledge } = useNotifications();
  const [filter, setFilter] = useState<AlertFilter>("Todas");
  const [selectedAlertId, setSelectedAlertId] = useState<number | null>(null);
  const [filterSheetOpen, setFilterSheetOpen] = useState(false);

  useEffect(() => {
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, []);

  const visibleAlerts = notifications.filter((alert) => {
    return filter === "Todas" || (filter === "Pendientes" && !alert.acknowledged) || (filter === "Reconocidas" && alert.acknowledged);
  });
  const selectedAlert = notifications.find((alert) => alert.id === selectedAlertId) ?? null;

  return (
    <PanelModal
      eyebrow="MONITOREO GLOBAL"
      title="Alertas"
      titleId="alerts-panel-title"
      onClose={() => onClose?.()}
      className="alerts-panel-modal"
      meta={<p className="alerts-summary"><strong>{notifications.filter((alert) => alert.severity === "critical" && !alert.acknowledged).length}</strong> alertas críticas sin reconocer · <strong>{notifications.length}</strong> en historial</p>}
      actions={<button className="alerts-mobile-filter" type="button" onClick={() => setFilterSheetOpen(true)}>{icons.filter}<span>Filtrar</span></button>}
    >
      <section className="alerts-screen">
        {selectedAlert ? <AlertModal alert={selectedAlert} onBack={() => setSelectedAlertId(null)} onAcknowledge={() => { acknowledge(selectedAlert.id); setSelectedAlertId(null); }} onViewUnit={() => { setSelectedAlertId(null); navigate(`/unit/${selectedAlert.unit.toLowerCase()}`); }} /> : <>
          <div className="alerts-history-layout">
            <aside className="alerts-history-nav">
              <h2>Notificaciones</h2>
              <div className="alerts-filters" role="tablist" aria-label="Filtros de alertas">
        {([["tune", "Todas"], ["schedule", "Pendientes"], ["task_alt", "Reconocidas"]] as const).map(([icon, item]) => <button className={filter === item ? "is-selected" : ""} type="button" role="tab" aria-selected={filter === item} onClick={() => setFilter(item)} key={item}><span className="material-symbols-rounded">{icon}</span><span>{item}</span></button>)}
              </div>
            </aside>
            <div className="alerts-history-content">
              <header className="alerts-history-content__header"><strong>Alertas de la unidad</strong><span>Selecciona una notificación para ver su detalle.</span></header>
          {visibleAlerts.length === 0 ? <EmptyAlerts /> : <div className="alerts-table" role="table" aria-label="Alertas de la unidad">
        <div className="alerts-table__head" role="row"><span>SEVERIDAD</span><span>UNIDAD</span><span>DESCRIPCIÓN DEL EVENTO</span><span>TIMESTAMP</span><span>ESTADO</span><span>ACCIÓN</span></div>
        <div className="alerts-table__body">{visibleAlerts.map((alert) => <AlertRow key={alert.id} alert={alert} onOpen={() => setSelectedAlertId(alert.id)} />)}</div>
          </div>}
            </div>
          </div>
          {filterSheetOpen && <div className="alerts-filter-sheet-backdrop" role="presentation" onClick={() => setFilterSheetOpen(false)}><div className="alerts-filter-sheet" role="dialog" aria-label="Filtros de alertas" onClick={(event) => event.stopPropagation()}><span className="alerts-sheet-handle" /><header><h2>Filtrar alertas</h2><button type="button" onClick={() => setFilterSheetOpen(false)} aria-label="Cerrar filtros">{icons.close}</button></header><div className="alerts-sheet-options">{(["Todas", "Pendientes", "Reconocidas"] as AlertFilter[]).map((item) => <button className={filter === item ? "is-selected" : ""} type="button" onClick={() => { setFilter(item); setFilterSheetOpen(false); }} key={item}>{item}</button>)}</div></div></div>}
          </>}
      </section>
    </PanelModal>
  );
}
