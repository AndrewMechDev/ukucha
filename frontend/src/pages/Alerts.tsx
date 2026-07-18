import { useState } from "react";
import { useNavigate } from "react-router-dom";

type Severity = "critical" | "caution";
type AlertFilter = "Todas" | "Críticas" | "Advertencias";

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
};

function SeverityTag({ severity }: { severity: Severity }) {
  return <span className={`alerts-status-tag alerts-status-tag--${severity}`}>{severity === "critical" ? "CRÍTICA" : "ADVERTENCIA"}</span>;
}

export function EmptyAlerts() {
  return <div className="alerts-empty"><span className="alerts-empty__badge"><i /> SEGURO</span><h2>Sin alertas activas — todo en orden</h2></div>;
}

function AlertModal({ alert, onClose, onAcknowledge, onViewUnit }: { alert: Alert; onClose: () => void; onAcknowledge: () => void; onViewUnit: () => void }) {
  return (
    <div className="alerts-modal-backdrop" role="presentation">
      <section className="alerts-modal" role="dialog" aria-modal="true" aria-labelledby="alert-modal-title">
        <header><div><p className="eyebrow">CONFIRMAR ALERTA</p><h2 id="alert-modal-title">Confirmar Alerta {alert.severity === "critical" ? "Crítica" : "de Precaución"}</h2></div><button type="button" onClick={onClose} aria-label="Cerrar modal">{icons.close}</button></header>
        <div className={`alerts-modal__summary alerts-modal__summary--${alert.severity}`}><SeverityTag severity={alert.severity} /><strong>{alert.unit} · {alert.zone}</strong><p>{alert.description}</p><time>{alert.timestamp} · {alert.age}</time></div>
        <div className="alerts-modal__recommendation"><p>RECOMENDACIÓN DEL COPILOTO</p><strong>{alert.recommendation}</strong></div>
        <div className="alerts-modal__actions"><button className="alerts-secondary-button" type="button" onClick={onViewUnit}>Ver unidad</button><button className="alerts-secondary-button" type="button" onClick={onClose}>Cerrar</button>{!alert.acknowledged && <button className="alerts-primary-button" type="button" onClick={onAcknowledge}>Reconocer alerta</button>}</div>
      </section>
    </div>
  );
}

function AlertRow({ alert, onOpen, onAcknowledge }: { alert: Alert; onOpen: () => void; onAcknowledge: () => void }) {
  return (
    <article className={`alert-row alert-row--${alert.severity}${alert.acknowledged ? " alert-row--acknowledged" : ""}`} onClick={onOpen}>
      <span><SeverityTag severity={alert.severity} /></span>
      <span className="alert-unit"><strong>{alert.unit}</strong><small>{alert.zone}</small></span>
      <span className="alert-description">{alert.description}</span>
      <time>{alert.timestamp}</time>
      <span className="alert-state">{alert.acknowledged ? <>{icons.check}<span>Reconocida</span></> : <span>Pendiente</span>}</span>
      <span className="alert-action">{alert.acknowledged ? icons.check : <button type="button" onClick={(event) => { event.stopPropagation(); onAcknowledge(); }}>Reconocer</button>}</span>
    </article>
  );
}

export default function Alerts() {
  const navigate = useNavigate();
  const [filter, setFilter] = useState<AlertFilter>("Todas");
  const [unitFilter, setUnitFilter] = useState("Todas las unidades");
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);
  const [filterSheetOpen, setFilterSheetOpen] = useState(false);
  const [acknowledgedIds, setAcknowledgedIds] = useState<number[]>([]);

  const visibleAlerts = alerts.filter((alert) => {
    const severityMatch = filter === "Todas" || (filter === "Críticas" && alert.severity === "critical") || (filter === "Advertencias" && alert.severity === "caution");
    return severityMatch && (unitFilter === "Todas las unidades" || alert.unit === unitFilter);
  }).map((alert) => acknowledgedIds.includes(alert.id) ? { ...alert, acknowledged: true } : alert);

  const acknowledge = (alert: Alert) => {
    setAcknowledgedIds((ids) => ids.includes(alert.id) ? ids : [...ids, alert.id]);
    setSelectedAlert(null);
  };

  return (
    <section className="alerts-screen">
      <header className="alerts-header">
        <div><p className="eyebrow">MONITOREO GLOBAL</p><h1>Centro de Alertas</h1><p className="alerts-summary"><strong>2</strong> alertas críticas sin reconocer · <strong>5</strong> hoy</p></div>
        <button className="alerts-mobile-filter" type="button" onClick={() => setFilterSheetOpen(true)}>{icons.filter}<span>Filtrar</span></button>
      </header>
      <div className="alerts-filters" role="tablist" aria-label="Filtros de alertas">
        {(["Todas", "Críticas", "Advertencias"] as AlertFilter[]).map((item) => <button className={filter === item ? "is-selected" : ""} type="button" role="tab" aria-selected={filter === item} onClick={() => setFilter(item)} key={item}>{item}</button>)}
        <select aria-label="Filtrar por unidad" value={unitFilter} onChange={(event) => setUnitFilter(event.target.value)}><option>Todas las unidades</option><option>Ukucha-01</option><option>Ukucha-02</option><option>Ukucha-03</option><option>Ukucha-04</option></select>
      </div>
      {visibleAlerts.length === 0 ? <EmptyAlerts /> : <div className="alerts-table" role="table" aria-label="Alertas de la flota">
        <div className="alerts-table__head" role="row"><span>SEVERIDAD</span><span>UNIDAD</span><span>DESCRIPCIÓN DEL EVENTO</span><span>TIMESTAMP</span><span>ESTADO</span><span>ACCIÓN</span></div>
        <div className="alerts-table__body">{visibleAlerts.map((alert) => <AlertRow key={alert.id} alert={alert} onOpen={() => setSelectedAlert(alert)} onAcknowledge={() => acknowledge(alert)} />)}</div>
      </div>}
      {filterSheetOpen && <div className="alerts-filter-sheet-backdrop" role="presentation" onClick={() => setFilterSheetOpen(false)}><div className="alerts-filter-sheet" role="dialog" aria-label="Filtros de alertas" onClick={(event) => event.stopPropagation()}><span className="alerts-sheet-handle" /><header><h2>Filtrar alertas</h2><button type="button" onClick={() => setFilterSheetOpen(false)} aria-label="Cerrar filtros">{icons.close}</button></header><div className="alerts-sheet-options">{(["Todas", "Críticas", "Advertencias"] as AlertFilter[]).map((item) => <button className={filter === item ? "is-selected" : ""} type="button" onClick={() => { setFilter(item); setFilterSheetOpen(false); }} key={item}>{item}</button>)}<select aria-label="Filtrar unidades" value={unitFilter} onChange={(event) => { setUnitFilter(event.target.value); setFilterSheetOpen(false); }}><option>Todas las unidades</option><option>Ukucha-01</option><option>Ukucha-02</option><option>Ukucha-03</option><option>Ukucha-04</option></select></div></div></div>}
      {selectedAlert && <AlertModal alert={selectedAlert} onClose={() => setSelectedAlert(null)} onAcknowledge={() => acknowledge(selectedAlert)} onViewUnit={() => { setSelectedAlert(null); navigate(`/unit/${selectedAlert.unit.toLowerCase()}`); }} />}
    </section>
  );
}
