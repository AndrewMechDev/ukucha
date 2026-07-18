import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  AudioMetricCard,
  EnvironmentMetricCard,
  LocationMetricCard,
  type TelemetrySnapshot,
} from "../components/TelemetryCards";

type UnitStatus = "safe" | "caution" | "critical" | "offline";

type Unit = {
  id: string;
  zone: string;
  status: UnitStatus;
  statusLabel: string;
  updated: string;
  telemetry: TelemetrySnapshot;
};

const units: Unit[] = [
  { id: "Ukucha-01", zone: "Zona Norte", status: "safe", statusLabel: "SEGURO", updated: "hace 12s", telemetry: { audio: { left: 6.5, right: 5.6 }, environment: { temperatureC: 28.4, humidityPercent: 34.2, pressureHpa: 783.1 }, gps: { latitude: -16.3988, longitude: -71.5369, valid: true } } },
  { id: "Ukucha-02", zone: "Zona Sur", status: "caution", statusLabel: "PRECAUCIÓN", updated: "hace 38s", telemetry: { audio: { left: 12.4, right: 10.8 }, environment: { temperatureC: 29.1, humidityPercent: 36.8, pressureHpa: 782.9 }, gps: { latitude: -16.3994, longitude: -71.5358, valid: true } } },
  { id: "Ukucha-03", zone: "Zona Este", status: "critical", statusLabel: "CRÍTICO", updated: "hace 4s", telemetry: { audio: { left: 14.3, right: 12.7 }, environment: { temperatureC: 29.2, humidityPercent: 33.5, pressureHpa: 783.0 }, gps: { latitude: -16.3979, longitude: -71.5347, valid: true } } },
  { id: "Ukucha-04", zone: "Zona Oeste", status: "offline", statusLabel: "OFFLINE", updated: "hace 18m", telemetry: { audio: { left: null, right: null }, environment: { temperatureC: null, humidityPercent: null, pressureHpa: null }, gps: { latitude: null, longitude: null, valid: false } } },
];

const icons = {
  link: <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m10 13 4-4M8.5 15.5l-2 2a3.5 3.5 0 0 1-5-5l4-4a3.5 3.5 0 0 1 5 0M15.5 8.5l2-2a3.5 3.5 0 0 1 5 5l-4 4a3.5 3.5 0 0 1-5 0" /></svg>,
  plus: <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14M5 12h14" /></svg>,
  close: <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18" /></svg>,
};

function UnitCard({ unit, onSelect }: { unit: Unit; onSelect: (unit: Unit) => void }) {
  return (
    <article
      className={`fleet-unit-card fleet-unit-card--${unit.status}`}
      role={unit.status === "offline" ? undefined : "link"}
      tabIndex={unit.status === "offline" ? -1 : 0}
      onClick={() => onSelect(unit)}
      onKeyDown={(event) => {
        if (unit.status !== "offline" && (event.key === "Enter" || event.key === " ")) onSelect(unit);
      }}
      title={unit.status === "offline" ? "Sin señal" : `Abrir dashboard de ${unit.id}`}
      aria-label={`${unit.id}, ${unit.statusLabel}, ${unit.zone}`}
    >
      <header className="fleet-unit-card__heading">
        <div><p className="fleet-unit-card__overline">UNIDAD DE CAMPO</p><h2>{unit.id}</h2><span>{unit.zone}</span></div>
        <div className="fleet-unit-card__status"><span className={`fleet-status-tag fleet-status-tag--${unit.status}`}>{unit.statusLabel}</span><time>{unit.updated}</time></div>
      </header>
      <div className="fleet-unit-card__metrics">
        <EnvironmentMetricCard temperature={unit.telemetry.environment.temperatureC} humidity={unit.telemetry.environment.humidityPercent} size="compact" />
        <AudioMetricCard left={unit.telemetry.audio.left} right={unit.telemetry.audio.right} size="compact" />
      </div>
      <LocationMetricCard latitude={unit.telemetry.gps.latitude} longitude={unit.telemetry.gps.longitude} valid={unit.telemetry.gps.valid} zone={unit.zone} size="compact" />
      <footer className="fleet-unit-card__footer"><span>PRESIÓN</span><strong>{unit.telemetry.environment.pressureHpa === null ? "N/D" : `${unit.telemetry.environment.pressureHpa.toFixed(1)} hPa`}</strong><b>{unit.status === "offline" ? "SIN DATOS" : "ABRIR DASHBOARD →"}</b></footer>
    </article>
  );
}

function EmptyFleetState({ onLink }: { onLink: () => void }) {
  return (
    <div className="fleet-empty">
      <div className="fleet-empty__icon">{icons.link}</div>
      <h2>Sin unidades registradas</h2>
      <p>Vincula una unidad para comenzar a monitorear tu flota.</p>
      <button className="primary-button" type="button" onClick={onLink}>{icons.link}<span>Vincular unidad</span></button>
    </div>
  );
}

function LinkUnitModal({ onClose }: { onClose: () => void }) {
  return (
    <div className="fleet-modal-backdrop" role="presentation">
      <section className="fleet-modal" role="dialog" aria-modal="true" aria-labelledby="link-unit-title">
        <header><div><p className="eyebrow">NUEVA CONEXIÓN</p><h2 id="link-unit-title">Vincular Nueva Unidad</h2></div><button type="button" onClick={onClose} aria-label="Cerrar modal">{icons.close}</button></header>
        <p className="fleet-modal__description">Introduce el identificador de la unidad para añadirla a la flota.</p>
        <label className="fleet-field"><span>ID DE UNIDAD</span><input autoFocus placeholder="Ej. UKUCHA-05" /></label>
        <div className="fleet-modal__actions"><button className="secondary-button" type="button" onClick={onClose}>Cancelar</button><button className="primary-button" type="button" onClick={onClose}>Vincular unidad</button></div>
      </section>
    </div>
  );
}

export default function Home() {
  const navigate = useNavigate();
  const [modalOpen, setModalOpen] = useState(false);

  const selectUnit = (unit: Unit) => {
    if (unit.status !== "offline") navigate(`/unit/${unit.id.toLowerCase()}`);
  };

  return (
    <section className="fleet-screen">
      <header className="fleet-header">
        <div><p className="eyebrow">OPERACIÓN EN CURSO</p><h1>Flota</h1><p className="fleet-summary"><strong>3</strong> unidades activas · <strong>1</strong> en alerta</p></div>
        <button className="primary-button fleet-link-button" type="button" onClick={() => setModalOpen(true)}>{icons.plus}<span>Vincular unidad</span></button>
      </header>
      <div className="fleet-grid" aria-label="Unidades de la flota">
        {units.map((unit) => <UnitCard unit={unit} onSelect={selectUnit} key={unit.id} />)}
      </div>
      {modalOpen && <LinkUnitModal onClose={() => setModalOpen(false)} />}
    </section>
  );
}

export { EmptyFleetState };
