import { useState } from "react";
import { useNavigate } from "react-router-dom";

type UnitStatus = "safe" | "caution" | "critical" | "offline";

type Unit = {
  id: string;
  zone: string;
  status: UnitStatus;
  statusLabel: string;
  battery: string;
  signal: string;
  updated: string;
  hasVideo: boolean;
};

const units: Unit[] = [
  { id: "Ukucha-01", zone: "Zona Norte", status: "safe", statusLabel: "SEGURO", battery: "74%", signal: "Tether estable", updated: "12s", hasVideo: true },
  { id: "Ukucha-02", zone: "Zona Sur", status: "caution", statusLabel: "PRECAUCIÓN", battery: "51%", signal: "Señal débil", updated: "38s", hasVideo: true },
  { id: "Ukucha-03", zone: "Zona Este", status: "critical", statusLabel: "CRÍTICO", battery: "23%", signal: "Tether estable", updated: "4s", hasVideo: true },
  { id: "Ukucha-04", zone: "Zona Oeste", status: "offline", statusLabel: "OFFLINE", battery: "—", signal: "Sin señal", updated: "18m", hasVideo: false },
];

const icons = {
  link: <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m10 13 4-4M8.5 15.5l-2 2a3.5 3.5 0 0 1-5-5l4-4a3.5 3.5 0 0 1 5 0M15.5 8.5l2-2a3.5 3.5 0 0 1 5 5l-4 4a3.5 3.5 0 0 1-5 0" /></svg>,
  signal: <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 18h.01M7 14a8 8 0 0 1 10 0M4.5 10.5a12 12 0 0 1 15 0M12 21h.01" /></svg>,
  offline: <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m3 3 18 18M10.6 5.1A9 9 0 0 1 21 12M5.1 10.6A9 9 0 0 0 12 21M8.5 8.5A5 5 0 0 1 15.5 15.5M8 17l-2 2M16 7l2-2" /></svg>,
  plus: <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14M5 12h14" /></svg>,
  close: <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18" /></svg>,
};

function VideoThumbnail({ unit }: { unit: Unit }) {
  if (!unit.hasVideo) {
    return <div className="fleet-thumbnail fleet-thumbnail--offline"><span>{icons.offline}</span><p>SIN SEÑAL</p></div>;
  }

  return (
    <div className={`fleet-thumbnail fleet-thumbnail--${unit.status}`}>
      <span className="fleet-thumbnail__label">LIVE · CAM 03</span>
      <div className="fleet-thumbnail__texture" aria-hidden="true" />
      <span className="fleet-bracket fleet-bracket--tl" /><span className="fleet-bracket fleet-bracket--tr" /><span className="fleet-bracket fleet-bracket--bl" /><span className="fleet-bracket fleet-bracket--br" />
      <span className="fleet-thumbnail__detection">PERSONA 92%</span>
    </div>
  );
}

function UnitCard({ unit, onSelect }: { unit: Unit; onSelect: (unit: Unit) => void }) {
  return (
    <button
      className={`fleet-unit-card fleet-unit-card--${unit.status}`}
      type="button"
      disabled={unit.status === "offline"}
      onClick={() => onSelect(unit)}
      title={unit.status === "offline" ? "Sin señal" : `Abrir dashboard de ${unit.id}`}
      aria-label={`${unit.id}, ${unit.statusLabel}, ${unit.zone}`}
    >
      <VideoThumbnail unit={unit} />
      <div className="fleet-unit-card__body">
        <div className="fleet-unit-card__heading"><div><h2>{unit.id}</h2><p>{unit.zone}</p></div><span className={`fleet-status-tag fleet-status-tag--${unit.status}`}>{unit.statusLabel}</span></div>
        <div className="fleet-unit-card__meta">
          <span><b>BATERÍA</b><strong>{unit.battery}</strong></span>
          <span><b>SEÑAL</b><strong>{unit.signal}</strong></span>
          <span><b>ACTUALIZACIÓN</b><strong>hace {unit.updated}</strong></span>
        </div>
      </div>
    </button>
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
        <div><p className="eyebrow">OPERACIÓN EN CURSO</p><h1>Flota</h1><p className="fleet-summary"><strong>4</strong> unidades activas · <strong>1</strong> en alerta</p></div>
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
