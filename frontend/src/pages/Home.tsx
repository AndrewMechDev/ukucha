import { useState } from "react";

type Flyout = "timeline" | "copilot" | null;

const icons = {
  video: <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3" y="5" width="14" height="14" rx="2" /><path d="m17 10 4-2v8l-4-2" /></svg>,
  map: <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m3 6 6-3 6 3 6-3v15l-6 3-6-3-6 3V6Z" /><path d="M9 3v15M15 6v15" /></svg>,
  timeline: <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="8" /><path d="M12 7v5l3 2" /></svg>,
  copilot: <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 6h14v10H9l-4 3V6Z" /><path d="M8 10h.01M12 10h.01M16 10h.01" /></svg>,
  speaker: <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 10v4h4l5 4V6l-5 4H4Z" /><path d="M17 9a5 5 0 0 1 0 6M19.5 6.5a9 9 0 0 1 0 11" /></svg>,
  alert: <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m12 3 9 17H3L12 3Z" /><path d="M12 9v4M12 17h.01" /></svg>,
  reconnect: <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 11a8 8 0 0 0-14-4L4 9M4 5v4h4M4 13a8 8 0 0 0 14 4l2-2M20 19v-4h-4" /></svg>,
};

function VideoCanvas({ mapView }: { mapView: boolean }) {
  return (
    <div className={`mission-canvas${mapView ? " mission-canvas--map" : ""}`}>
      {mapView ? (
        <div className="mission-map" aria-label="Mapa táctico de Zona Norte">
          <span className="mission-map__route" /><span className="mission-map__unit">U03</span><span className="mission-map__point mission-map__point--one" /><span className="mission-map__point mission-map__point--two" />
          <span className="mission-map__coordinate">34° 36&apos; 12&quot; N<br />58° 22&apos; 04&quot; O</span>
        </div>
      ) : (
        <>
          <div className="mission-video-texture" aria-hidden="true" />
          <span className="mission-video-label">LIVE · CAM 03</span>
          <button className="yolo-detection" type="button" aria-label="Abrir detalle de detección de persona">
            <span className="yolo-detection__corner yolo-detection__corner--tl" /><span className="yolo-detection__corner yolo-detection__corner--tr" /><span className="yolo-detection__corner yolo-detection__corner--bl" /><span className="yolo-detection__corner yolo-detection__corner--br" /><span className="yolo-detection__label">PERSONA 92%</span>
          </button>
          <span className="yolo-detection__hint">Clic para detalle de detección</span>
        </>
      )}
    </div>
  );
}

function SensorRail({ collapsed, onToggle }: { collapsed: boolean; onToggle: () => void }) {
  const sensors = [
    ["O₂", "19.6%", "safe"],
    ["CO", "12 ppm", "caution"],
    ["BATERÍA ROBOT", "74%", "safe"],
    ["SEÑAL TETHER", "ESTABLE", "safe"],
  ];

  return (
    <aside className={`sensor-rail${collapsed ? " sensor-rail--collapsed" : ""}`}>
      <button className="sensor-rail__toggle" type="button" onClick={onToggle} aria-label={collapsed ? "Mostrar sensores" : "Ocultar sensores"} aria-expanded={!collapsed}>
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d={collapsed ? "m9 6 6 6-6 6" : "m15 6-6 6 6 6"} /></svg>
      </button>
      <div className="sensor-rail__content">
        <p className="sensor-rail__title">TELEMETRÍA</p>
        {sensors.map(([label, value, state]) => (
          <article className="rail-sensor" key={label}><span className={`rail-sensor__dot rail-sensor__dot--${state}`} /><p>{label}</p><strong>{value}</strong></article>
        ))}
      </div>
    </aside>
  );
}

function TtsConsole({ expanded, onToggle }: { expanded: boolean; onToggle: () => void }) {
  return (
    <div className={`mission-tts${expanded ? " mission-tts--expanded" : ""}`}>
      <button className="mission-tts__bar" type="button" onClick={onToggle} aria-expanded={expanded}>
        {icons.speaker}<span>Comunicación por voz</span><svg className="mission-tts__chevron" viewBox="0 0 24 24" aria-hidden="true"><path d="m7 10 5 5 5-5" /></svg>
      </button>
      {expanded && <div className="mission-tts__body">
        <div className="mission-tts__phrases">{["Mantén la calma", "Ayuda en camino", "¿Puedes escucharme?"].map((phrase) => <button type="button" key={phrase}>{phrase}</button>)}</div>
        <div className="mission-tts__input"><input aria-label="Mensaje de comunicación" placeholder="Escribe un mensaje..." /><button type="button">Enviar por buzzer</button></div>
        <div className="mission-tts__transcript"><p><time>10:22:04</time> Unidad 03, ¿puedes confirmar tu posición?</p><p><time>10:22:11</time> Posición confirmada. Avanzando a Zona Norte.</p><p><time>10:22:18</time> Mensaje enviado a la unidad <span className="mission-waveform"><i /><i /><i /><i /><i /></span></p></div>
      </div>}
    </div>
  );
}

function TimelineFlyout() {
  return <div className="mission-flyout__content"><div className="flyout-timeline-item flyout-timeline-item--critical"><span>{icons.alert}</span><div><strong>Persona detectada</strong><p>hace 2 min</p></div><time>10:22</time></div><div className="flyout-timeline-item flyout-timeline-item--caution"><span>{icons.alert}</span><div><strong>Alerta de gas</strong><p>hace 8 min</p></div><time>10:16</time></div><div className="flyout-timeline-item"><span>{icons.reconnect}</span><div><strong>Reconexión</strong><p>hace 15 min</p></div><time>10:09</time></div></div>;
}

function CopilotFlyout() {
  return <div className="mission-flyout__content"><div className="copilot-entry"><time>10:21:58</time><p>Zona 3: O₂ al 19.6%, cerca del límite legal. Prioridad alta.</p></div><div className="copilot-entry"><time>10:22:06</time><p>Persona detectada a 12 m. Recomiendo mantener el canal de voz abierto.</p></div><div className="copilot-entry"><time>10:22:14</time><p>Ruta despejada hacia el punto de extracción norte.</p></div><label className="copilot-query"><input placeholder="Preguntar al copiloto..." /><span>↵</span></label></div>;
}

export default function Home() {
  const [mapView, setMapView] = useState(false);
  const [railCollapsed, setRailCollapsed] = useState(false);
  const [ttsExpanded, setTtsExpanded] = useState(false);
  const [flyout, setFlyout] = useState<Flyout>(null);

  return (
    <section className="mission-screen">
      <div className="mission-stage">
        <VideoCanvas mapView={mapView} />
        <div className="mission-nav-wrap">
          <nav className="mission-nav" aria-label="Controles de unidad">
            <div className="mission-nav__identity"><strong>Ukucha-03</strong><span>Zona Norte</span><b><i /> En vivo</b></div>
            <div className="mission-nav__view segmented-control" role="tablist" aria-label="Vista principal">
              <button className={!mapView ? "is-selected" : ""} type="button" role="tab" aria-selected={!mapView} onClick={() => setMapView(false)}>{icons.video} Video</button>
              <button className={mapView ? "is-selected" : ""} type="button" role="tab" aria-selected={mapView} onClick={() => setMapView(true)}>{icons.map} Mapa</button>
            </div>
            <div className="mission-nav__actions">
              <button className={flyout === "timeline" ? "is-active" : ""} type="button" onClick={() => setFlyout(flyout === "timeline" ? null : "timeline")}>{icons.timeline}<span>Timeline</span></button>
              <button className={flyout === "copilot" ? "is-active" : ""} type="button" onClick={() => setFlyout(flyout === "copilot" ? null : "copilot")}>{icons.copilot}<span>Copiloto IA</span></button>
            </div>
          </nav>
          {flyout && <div className={`mission-flyout mission-flyout--${flyout}`}><span className="mission-flyout__pointer" aria-hidden="true" /> <header><h2>{flyout === "timeline" ? "Timeline de eventos" : "Copiloto IA"}</h2><button type="button" onClick={() => setFlyout(null)} aria-label="Cerrar panel">×</button></header>{flyout === "timeline" ? <TimelineFlyout /> : <CopilotFlyout />}</div>}
        </div>

        <SensorRail collapsed={railCollapsed} onToggle={() => setRailCollapsed((value) => !value)} />
        <div className="golden-hours golden-hours--mission"><span>GOLDEN HOURS</span><strong>01:42:18</strong></div>
        <TtsConsole expanded={ttsExpanded} onToggle={() => setTtsExpanded((value) => !value)} />
      </div>
    </section>
  );
}
