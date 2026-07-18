import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  UnitSummaryCard,
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
  { id: "Ukucha-01", zone: "Zona Norte", status: "safe", statusLabel: "Seguro", updated: "hace 12s", telemetry: { audio: { left: 6.5, right: 5.6 }, environment: { temperatureC: 28.4, humidityPercent: 34.2, pressureHpa: 783.1 }, gps: { latitude: -16.3988, longitude: -71.5369, valid: true } } },
  { id: "Ukucha-02", zone: "Zona Sur", status: "caution", statusLabel: "Precaución", updated: "hace 38s", telemetry: { audio: { left: 12.4, right: 10.8 }, environment: { temperatureC: 29.1, humidityPercent: 36.8, pressureHpa: 782.9 }, gps: { latitude: -16.3994, longitude: -71.5358, valid: true } } },
  { id: "Ukucha-03", zone: "Zona Este", status: "critical", statusLabel: "Crítico", updated: "hace 4s", telemetry: { audio: { left: 14.3, right: 12.7 }, environment: { temperatureC: 29.2, humidityPercent: 33.5, pressureHpa: 783.0 }, gps: { latitude: -16.3979, longitude: -71.5347, valid: true } } },
  { id: "Ukucha-04", zone: "Zona Oeste", status: "offline", statusLabel: "Offline", updated: "hace 18m", telemetry: { audio: { left: null, right: null }, environment: { temperatureC: null, humidityPercent: null, pressureHpa: null }, gps: { latitude: null, longitude: null, valid: false } } },
];

const icons = {
  link: <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m10 13 4-4M8.5 15.5l-2 2a3.5 3.5 0 0 1-5-5l4-4a3.5 3.5 0 0 1 5 0M15.5 8.5l2-2a3.5 3.5 0 0 1 5 5l-4 4a3.5 3.5 0 0 1-5 0" /></svg>,
  wifi: <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 8.5a16 16 0 0 1 20 0M5 12a11 11 0 0 1 14 0M8.5 15.5a6 6 0 0 1 7 0M12 19h.01" /></svg>,
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
      <UnitSummaryCard battery={unit.status === "critical" ? 42 : unit.status === "caution" ? 58 : 70} sensorValue={unit.status === "critical" ? "19.6%" : "28.4°C"} sensorLabel={unit.status === "critical" ? "O₂" : "TEMP"} />
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

type LinkStep = "methods" | "scanning" | "results" | "success";

function LinkUnitModal({ onClose }: { onClose: () => void }) {
  const [step, setStep] = useState<LinkStep>("methods");

  useEffect(() => {
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, []);

  useEffect(() => {
    if (step !== "scanning") return undefined;
    const timer = window.setTimeout(() => setStep("results"), 2200);
    return () => window.clearTimeout(timer);
  }, [step]);

  const connectUnit = () => setStep("success");

  if (step === "scanning") {
    return (
      <div className="fleet-modal-backdrop" role="presentation">
        <section className="fleet-modal fleet-modal--scanner" role="dialog" aria-modal="true" aria-labelledby="scan-title">
          <header><div><p className="eyebrow">NUEVA CONEXIÓN</p><h2 id="scan-title">Buscando Ukuchas</h2></div><button type="button" onClick={onClose} aria-label="Cerrar modal">{icons.close}</button></header>
          <div className="fleet-scanner" aria-live="polite">
            <div className="fleet-scanner__waves"><span /><span /><span /><b>{icons.wifi}</b></div>
            <strong>Escaneando frecuencias de telemetría...</strong>
            <span>Buscando unidades disponibles en tu red Wi‑Fi</span>
          </div>
        </section>
      </div>
    );
  }

  if (step === "results") {
    return (
      <div className="fleet-modal-backdrop" role="presentation">
        <section className="fleet-modal fleet-modal--results" role="dialog" aria-modal="true" aria-labelledby="results-title">
          <header><div><p className="eyebrow">RED LOCAL</p><h2 id="results-title">Ukuchas disponibles</h2></div><button type="button" onClick={onClose} aria-label="Cerrar modal">{icons.close}</button></header>
          <p className="fleet-modal__description">Selecciona una unidad para conectarla a tu flota.</p>
          <div className="fleet-discovered-list">
            <button type="button" className="fleet-discovered-unit" onClick={connectUnit}><span className="fleet-discovered-unit__signal">⌁</span><span><strong>Ukucha-05</strong><small>Zona Norte · Señal excelente</small></span><b>Conectar →</b></button>
            <button type="button" className="fleet-discovered-unit" onClick={connectUnit}><span className="fleet-discovered-unit__signal">⌁</span><span><strong>Ukucha-06</strong><small>Zona Sur · Señal buena</small></span><b>Conectar →</b></button>
          </div>
          <button className="secondary-button fleet-rescan" type="button" onClick={() => setStep("scanning")}>↻ Buscar de nuevo</button>
        </section>
      </div>
    );
  }

  if (step === "success") {
    return (
      <div className="fleet-modal-backdrop" role="presentation">
        <section className="fleet-modal fleet-modal--success" role="dialog" aria-modal="true" aria-labelledby="success-title">
          <div className="fleet-success-icon">✓</div>
          <p className="eyebrow">CONEXIÓN COMPLETADA</p>
          <h2 id="success-title">Ukucha-05 conectada</h2>
          <p className="fleet-modal__description">La unidad ya está transmitiendo datos en tu red Wi‑Fi.</p>
          <button className="primary-button" type="button" onClick={onClose}>Ver unidad</button>
        </section>
      </div>
    );
  }

  return (
    <div className="fleet-modal-backdrop" role="presentation">
      <section className="fleet-modal" role="dialog" aria-modal="true" aria-labelledby="link-unit-title">
        <header><div><p className="eyebrow">NUEVA CONEXIÓN</p><h2 id="link-unit-title">Vincular Nueva Unidad</h2></div><button type="button" onClick={onClose} aria-label="Cerrar modal">{icons.close}</button></header>
        <p className="fleet-modal__description">Busca las unidades disponibles en tu red local para añadirlas a la flota.</p>
        <div className="fleet-connection-methods">
          <button type="button" className="fleet-connection-method" onClick={() => setStep("scanning")}><span className="fleet-method-icon">{icons.wifi}</span><span><strong>Vía Wi‑Fi</strong><small>Detección automática en la red local</small></span><b>→</b></button>
          <button type="button" className="fleet-connection-method fleet-connection-method--disabled" disabled><span className="fleet-method-icon">ᛒ</span><span><strong>Vía Bluetooth</strong><small>Próximamente disponible</small></span><b>→</b></button>
        </div>
      </section>
    </div>
  );
}

export default function Home() {
  const navigate = useNavigate();
  const [modalOpen, setModalOpen] = useState(false);

  const selectUnit = (unit: Unit) => {
    if (unit.status !== "offline") navigate(`/unit/${unit.id.toLowerCase()}/sensors`);
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
