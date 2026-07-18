import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

type UnitInfo = { name: string; zone: string };
type Flyout = "timeline" | "copilot" | null;

const unitInfo: Record<string, UnitInfo> = {
  "ukucha-01": { name: "Ukucha-01", zone: "Zona Norte" },
  "ukucha-02": { name: "Ukucha-02", zone: "Zona Sur" },
  "ukucha-03": { name: "Ukucha-03", zone: "Zona Este" },
  "ukucha-04": { name: "Ukucha-04", zone: "Zona Oeste" },
};

const icons = {
  back: <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M19 12H5M11 6l-6 6 6 6" /></svg>,
  video: <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="5" width="14" height="14" rx="2" /><path d="m17 10 4-2v8l-4-2" /></svg>,
  map: <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m3 6 6-3 6 3 6-3v15l-6 3-6-3-6 3V6ZM9 3v15M15 6v15" /></svg>,
  timeline: <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="8" /><path d="M12 7v5l3 2" /></svg>,
  copilot: <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 6h14v10H9l-4 3V6Z" /><path d="M8 10h.01M12 10h.01M16 10h.01" /></svg>,
  close: <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18" /></svg>,
};

function UnitFlyout({ type, onClose }: { type: Exclude<Flyout, null>; onClose: () => void }) {
  return <div className={`unit-flyout unit-flyout--${type}`}><span className="unit-flyout__pointer" /><header><h2>{type === "timeline" ? "Timeline de eventos" : "Copiloto IA"}</h2><button type="button" onClick={onClose} aria-label="Cerrar">{icons.close}</button></header>{type === "timeline" ? <div className="unit-flyout__list"><p><strong>Persona detectada</strong><span>hace 2 min · 10:22</span></p><p><strong>Alerta de gas</strong><span>hace 8 min · 10:16</span></p><p><strong>Reconexión</strong><span>hace 15 min · 10:09</span></p></div> : <div className="unit-flyout__list"><p><strong>Zona 3: O₂ al 19.6%</strong><span>Prioridad alta.</span></p><p><strong>Persona detectada a 12 m.</strong><span>Mantener canal de voz abierto.</span></p><input placeholder="Preguntar al copiloto..." /></div>}</div>;
}

export default function UnitDashboard() {
  const navigate = useNavigate();
  const { unitId = "ukucha-03" } = useParams();
  const unit = unitInfo[unitId.toLowerCase()] ?? { name: unitId, zone: "Zona desconocida" };
  const [mapView, setMapView] = useState(false);
  const [flyout, setFlyout] = useState<Flyout>(null);
  const [detectionOpen, setDetectionOpen] = useState(false);

  const openTool = (tool: Exclude<Flyout, null>) => {
    if (window.matchMedia("(max-width: 599px)").matches) {
      navigate(`/${tool}`);
      return;
    }
    setFlyout(flyout === tool ? null : tool);
  };

  return (
    <section className="mission-screen">
      <div className="mission-stage">
        <div className={`mission-canvas${mapView ? " mission-canvas--map" : ""}`}>
          {mapView ? <div className="mission-map" aria-label={`Mapa táctico de ${unit.zone}`}><span className="mission-map__route" /><span className="mission-map__unit">U03</span><span className="mission-map__point mission-map__point--one" /><span className="mission-map__point mission-map__point--two" /></div> : <><div className="mission-video-texture" aria-hidden="true" /><span className="mission-video-label">LIVE · CAM 03</span><button className="yolo-detection" type="button" onClick={() => setDetectionOpen(true)} aria-label="Abrir detalle de detección de persona"><span className="yolo-detection__corner yolo-detection__corner--tl" /><span className="yolo-detection__corner yolo-detection__corner--tr" /><span className="yolo-detection__corner yolo-detection__corner--bl" /><span className="yolo-detection__corner yolo-detection__corner--br" /><span className="yolo-detection__label">PERSONA 92%</span></button></>}
        </div>
        <div className="unit-dashboard-nav-wrap">
          <nav className="unit-dashboard-nav" aria-label="Controles de unidad">
            <button className="unit-back-button" type="button" onClick={() => navigate("/")} aria-label="Volver a Flota">{icons.back}</button>
            <div className="unit-dashboard-identity"><strong>{unit.name}</strong><span>{unit.zone}</span><b><i /> En vivo</b></div>
            <div className="unit-dashboard-view segmented-control" role="tablist" aria-label="Vista principal"><button className={!mapView ? "is-selected" : ""} type="button" role="tab" aria-selected={!mapView} onClick={() => setMapView(false)}>{icons.video} Video</button><button className={mapView ? "is-selected" : ""} type="button" role="tab" aria-selected={mapView} onClick={() => setMapView(true)}>{icons.map} Mapa</button></div>
            <div className="unit-dashboard-actions"><button className={flyout === "timeline" ? "is-active" : ""} type="button" onClick={() => openTool("timeline")}>{icons.timeline}<span>Timeline</span></button><button className={flyout === "copilot" ? "is-active" : ""} type="button" onClick={() => openTool("copilot")}>{icons.copilot}<span>Copiloto IA</span></button></div>
          </nav>
          {flyout && <UnitFlyout type={flyout} onClose={() => setFlyout(null)} />}
        </div>
        <div className="golden-hours golden-hours--mission"><span>GOLDEN HOURS</span><strong>01:42:18</strong></div>
        <aside className="unit-dashboard-sensors"><p>TELEMETRÍA</p>{[["O₂", "19.6%"], ["CO", "12 ppm"], ["BATERÍA", "74%"], ["TETHER", "ESTABLE"]].map(([label, value]) => <div key={label}><span>{label}</span><strong>{value}</strong></div>)}</aside>
        <div className="unit-dashboard-tts"><button type="button"><span>▸</span> Comunicación por voz <b>⌄</b></button></div>
      </div>
      {detectionOpen && <div className="unit-detection-modal-backdrop" role="presentation"><section className="unit-detection-modal" role="dialog" aria-modal="true" aria-labelledby="detection-title"><header><div><p className="eyebrow">DETALLE DE DETECCIÓN</p><h2 id="detection-title">Persona · confianza 92%</h2></div><button type="button" onClick={() => setDetectionOpen(false)} aria-label="Cerrar">{icons.close}</button></header><p>Detección capturada por {unit.name} en {unit.zone}.</p><button type="button" onClick={() => setDetectionOpen(false)}>Cerrar</button></section></div>}
    </section>
  );
}
