import { useState } from "react";
import { useNavigate } from "react-router-dom";
import StyledSelect from "../components/StyledSelect";

type Severity = "critical" | "caution";
type AlertFilter = "Todas" | "Pendientes" | "Reconocidas";

type Alert = {
  id: number;
  severity: Severity;
  unit: string;
  zone: string;
  description: string;
  timestamp: string;
  age: string;
  acknowledged: boolean;
  recommendation: string;
};

const alerts: Alert[] = [
  { id: 1, severity: "critical", unit: "Ukucha-03", zone: "Zona Este", description: "Persona detectada · confianza 92%", timestamp: "14:32:07", age: "hace 2 min", acknowledged: false, recommendation: "Mantener canal de voz abierto y preparar extracción por el corredor norte." },
  { id: 2, severity: "critical", unit: "Ukucha-01", zone: "Zona Norte", description: "O₂ bajo el límite normativo · 19.6%", timestamp: "14:28:44", age: "hace 5 min", acknowledged: false, recommendation: "Prioridad alta: desplazar la unidad fuera de la zona de concentración de gas." },
  { id: 3, severity: "caution", unit: "Ukucha-02", zone: "Zona Sur", description: "Señal tether débil", timestamp: "14:21:18", age: "hace 12 min", acknowledged: false, recommendation: "Reducir distancia al punto de enlace y verificar obstáculos del terreno." },
  { id: 4, severity: "caution", unit: "Ukucha-03", zone: "Zona Este", description: "Nivel de gas CO en umbral de precaución", timestamp: "14:16:03", age: "hace 17 min", acknowledged: true, recommendation: "Mantener monitorización continua del sensor de gas." },
  { id: 5, severity: "critical", unit: "Ukucha-04", zone: "Zona Oeste", description: "Unidad fuera de línea", timestamp: "13:58:26", age: "hace 35 min", acknowledged: true, recommendation: "Enviar equipo de recuperación al último punto conocido." },
  { id: 6, severity: "caution", unit: "Ukucha-01", zone: "Zona Norte", description: "Batería por debajo del 30% · 28%", timestamp: "13:44:12", age: "hace 49 min", acknowledged: true, recommendation: "Planificar retorno de la unidad antes de continuar la misión." },
  { id: 7, severity: "caution", unit: "Ukucha-02", zone: "Zona Sur", description: "Movimiento detectado fuera del perímetro", timestamp: "12:18:51", age: "hace 2 h", acknowledged: true, recommendation: "Revisar la cámara del sector y validar la detección." },
  { id: 8, severity: "critical", unit: "Ukucha-03", zone: "Zona Este", description: "Temperatura del motor elevada · 82°C", timestamp: "11:52:09", age: "hace 3 h", acknowledged: true, recommendation: "Detener avance y dejar enfriar el motor antes de retomar." },
];

const icons = {
  check: <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m5 12 4 4L19 6" /></svg>,
  close: <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18" /></svg>,
  filter: <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 6h16M7 12h10M10 18h4" /></svg>,
  detail: <span className="material-symbols-rounded" aria-hidden="true">open_in_full</span>,
};

function SeverityTag({ severity }: { severity: Severity }) {
  return <span className={`alerts-status-tag alerts-status-tag--${severity} alerts-filter-chip`}>{severity === "critical" ? "Crítica" : "Advertencia"}</span>;
}

export function EmptyAlerts() {
  return <div className="alerts-empty"><span className="alerts-empty__badge"><i /> SEGURO</span><h2>Sin alertas activas — todo en orden</h2></div>;
}

function AlertModal({ alert, onBack, onClose, onAcknowledge, onViewUnit }: { alert: Alert; onBack: () => void; onClose: () => void; onAcknowledge: () => void; onViewUnit: () => void }) {
  return (
    <section className="alerts-detail-view" aria-labelledby="alert-modal-title">
      <header className="alerts-detail-header">
        <button className="alerts-detail-back" type="button" onClick={onBack}><span className="material-symbols-rounded">arrow_back</span><span>Alertas</span></button>
        <button className="alerts-panel-close" type="button" onClick={onClose} aria-label="Cerrar alertas">{icons.close}</button>
      </header>
      <div className="alerts-detail-heading"><p className="eyebrow">DETALLE DE ALERTA</p><h2 id="alert-modal-title">{alert.severity === "critical" ? "Alerta crítica" : "Alerta de precaución"}</h2></div>
      <div className={`alerts-modal__summary alerts-modal__summary--${alert.severity}`}><SeverityTag severity={alert.severity} /><strong>{alert.unit} · {alert.zone}</strong><p>{alert.description}</p><time>{alert.timestamp} · {alert.age}</time></div>
      <div className="alerts-modal__recommendation"><p>RECOMENDACIÓN DEL COPILOTO</p><strong>{alert.recommendation}</strong></div>
      <div className="alerts-modal__actions"><button className="alerts-secondary-button" type="button" onClick={onViewUnit}>Ver unidad</button>{!alert.acknowledged && <button className="alerts-primary-button" type="button" onClick={onAcknowledge}>Reconocer alerta</button>}</div>
    </section>
  );
}

function AlertRow({ alert, onOpen }: { alert: Alert; onOpen: () => void }) {
  return (
    <article className={`alert-row alert-row--${alert.severity}${alert.acknowledged ? " alert-row--acknowledged" : ""}`} onClick={onOpen}>
      <span><SeverityTag severity={alert.severity} /></span>
      <span className="alert-unit"><strong>{alert.unit}</strong><small>{alert.zone}</small></span>
      <span className="alert-description">{alert.description}</span>
      <time>{alert.timestamp}</time>
      <span className={`alert-state alert-state-chip${alert.acknowledged ? " alert-state-chip--acknowledged" : " alert-state-chip--pending"}`}>{alert.acknowledged ? <>{icons.check}<span>Reconocida</span></> : <span>Pendiente</span>}</span>
      <span className="alert-action"><button className="alert-detail-button" type="button" aria-label={`Ver detalle de alerta de ${alert.unit}`} onClick={(event) => { event.stopPropagation(); onOpen(); }}>{icons.detail}</button></span>
    </article>
  );
}

export default function Alerts({ onClose }: { onClose?: () => void }) {
  const navigate = useNavigate();
  const [filter, setFilter] = useState<AlertFilter>("Todas");
  const [unitFilter, setUnitFilter] = useState("Todas las unidades");
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);
  const [filterSheetOpen, setFilterSheetOpen] = useState(false);
  const [acknowledgedIds, setAcknowledgedIds] = useState<number[]>([]);

  const visibleAlerts = alerts.filter((alert) => {
    const statusMatch = filter === "Todas" || (filter === "Pendientes" && !alert.acknowledged) || (filter === "Reconocidas" && alert.acknowledged);
    return statusMatch && (unitFilter === "Todas las unidades" || alert.unit === unitFilter);
  }).map((alert) => acknowledgedIds.includes(alert.id) ? { ...alert, acknowledged: true } : alert);

  const acknowledge = (alert: Alert) => {
    setAcknowledgedIds((ids) => ids.includes(alert.id) ? ids : [...ids, alert.id]);
    setSelectedAlert(null);
  };

  return (
    <div className="alerts-panel-backdrop" role="presentation" onClick={() => onClose?.()}>
      <section className="alerts-panel-modal" role="dialog" aria-modal="true" aria-labelledby="alerts-panel-title" onClick={(event) => event.stopPropagation()}>
        <section className="alerts-screen">
          {selectedAlert ? <AlertModal alert={selectedAlert} onBack={() => setSelectedAlert(null)} onClose={() => onClose?.()} onAcknowledge={() => acknowledge(selectedAlert)} onViewUnit={() => { setSelectedAlert(null); navigate(`/unit/${selectedAlert.unit.toLowerCase()}`); }} /> : <>
          <header className="alerts-header">
            <div><p className="eyebrow">MONITOREO GLOBAL</p><h1 id="alerts-panel-title">Alertas</h1><p className="alerts-summary"><strong>{alerts.filter((alert) => alert.severity === "critical" && !alert.acknowledged).length}</strong> alertas críticas sin reconocer · <strong>{alerts.length}</strong> en historial</p></div>
            <div className="alerts-header__actions"><button className="alerts-mobile-filter" type="button" onClick={() => setFilterSheetOpen(true)}>{icons.filter}<span>Filtrar</span></button><button className="alerts-panel-close" type="button" onClick={() => onClose?.()} aria-label="Cerrar alertas">{icons.close}</button></div>
          </header>
          <div className="alerts-history-layout">
            <aside className="alerts-history-nav">
              <p className="eyebrow">HISTORIAL</p>
              <h2>Notificaciones</h2>
              <div className="alerts-filters" role="tablist" aria-label="Filtros de alertas">
        {(["Todas", "Pendientes", "Reconocidas"] as AlertFilter[]).map((item) => <button className={filter === item ? "is-selected" : ""} type="button" role="tab" aria-selected={filter === item} onClick={() => setFilter(item)} key={item}>{item}</button>)}
        <StyledSelect ariaLabel="Filtrar por unidad" value={unitFilter} onChange={setUnitFilter} options={["Todas las unidades", "Ukucha-01", "Ukucha-02", "Ukucha-03", "Ukucha-04"].map((option) => ({ label: option, value: option }))} />
              </div>
            </aside>
            <div className="alerts-history-content">
              <header className="alerts-history-content__header"><strong>Alertas de la flota</strong><span>Selecciona una notificación para ver su detalle.</span></header>
          {visibleAlerts.length === 0 ? <EmptyAlerts /> : <div className="alerts-table" role="table" aria-label="Alertas de la flota">
        <div className="alerts-table__head" role="row"><span>SEVERIDAD</span><span>UNIDAD</span><span>DESCRIPCIÓN DEL EVENTO</span><span>TIMESTAMP</span><span>ESTADO</span><span>ACCIÓN</span></div>
        <div className="alerts-table__body">{visibleAlerts.map((alert) => <AlertRow key={alert.id} alert={alert} onOpen={() => setSelectedAlert(alert)} />)}</div>
          </div>}
            </div>
          </div>
          {filterSheetOpen && <div className="alerts-filter-sheet-backdrop" role="presentation" onClick={() => setFilterSheetOpen(false)}><div className="alerts-filter-sheet" role="dialog" aria-label="Filtros de alertas" onClick={(event) => event.stopPropagation()}><span className="alerts-sheet-handle" /><header><h2>Filtrar alertas</h2><button type="button" onClick={() => setFilterSheetOpen(false)} aria-label="Cerrar filtros">{icons.close}</button></header><div className="alerts-sheet-options">{(["Todas", "Pendientes", "Reconocidas"] as AlertFilter[]).map((item) => <button className={filter === item ? "is-selected" : ""} type="button" onClick={() => { setFilter(item); setFilterSheetOpen(false); }} key={item}>{item}</button>)}<StyledSelect ariaLabel="Filtrar unidades" value={unitFilter} onChange={(value) => { setUnitFilter(value); setFilterSheetOpen(false); }} options={["Todas las unidades", "Ukucha-01", "Ukucha-02", "Ukucha-03", "Ukucha-04"].map((option) => ({ label: option, value: option }))} /></div></div></div>}
          </>}
        </section>
      </section>
    </div>
  );
}
