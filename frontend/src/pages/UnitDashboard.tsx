import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  AudioMetricCard,
  ConnectionMetricCard,
  EnvironmentMetricCard,
  LocationMetricCard,
  PressureMetricCard,
  type TelemetrySnapshot,
} from "../components/TelemetryCards";
import { useLanguage } from "../components/LanguageContext";

type UnitInfo = { name: string; zone: string };
type Flyout = "timeline" | "copilot" | null;
const placeholderTelemetry: TelemetrySnapshot = {
  audio: { left: 6.5, right: 5.6 },
  environment: { temperatureC: 28.4, pressureHpa: 783.1, humidityPercent: 34.2 },
  gps: { latitude: -16.3988, longitude: -71.5369, valid: true },
};

const unitInfo: Record<string, UnitInfo> = {
  "ukucha-01": { name: "Ukucha-01", zone: "Zona Norte" },
  "ukucha-02": { name: "Ukucha-02", zone: "Zona Sur" },
  "ukucha-03": { name: "Ukucha-03", zone: "Zona Este" },
  "ukucha-04": { name: "Ukucha-04", zone: "Zona Oeste" },
};

const icons = {
  back: <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M19 12H5M11 6l-6 6 6 6" /></svg>,
  timeline: <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="8" /><path d="M12 7v5l3 2" /></svg>,
  copilot: <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 6h14v10H9l-4 3V6Z" /><path d="M8 10h.01M12 10h.01M16 10h.01" /></svg>,
  close: <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18" /></svg>,
};

function UnitFlyout({ type, onClose }: { type: Exclude<Flyout, null>; onClose: () => void }) {
  const { t, language } = useLanguage();
  return (
    <div className={`unit-flyout unit-flyout--${type}`}>
      <span className="unit-flyout__pointer" />
      <header>
        <h2>{type === "timeline" ? t("timeline_eventos") : t("copiloto_ia")}</h2>
        <button type="button" onClick={onClose} aria-label={t("cerrar")}>{icons.close}</button>
      </header>
      {type === "timeline" ? (
        <div className="unit-flyout__list">
          <p><strong>{t("persona_detectada")}</strong><span>{t("hace")} 2 {t("minutos_abr")} · 10:22</span></p>
          <p><strong>{t("alerta_de_gas")}</strong><span>{t("hace")} 8 {t("minutos_abr")} · 10:16</span></p>
          <p><strong>{t("reconexion")}</strong><span>{t("hace")} 15 {t("minutos_abr")} · 10:09</span></p>
        </div>
      ) : (
        <div className="unit-flyout__list">
          <p><strong>Zona 3: O₂ al 19.6%</strong><span>{language === "English" ? "High priority." : "Prioridad alta."}</span></p>
          <p><strong>{t("persona_detectada")} a 12 m.</strong><span>{language === "English" ? "Keep voice channel open." : "Mantener canal de voz abierto."}</span></p>
          <input placeholder={t("preguntar_copiloto")} />
        </div>
      )}
    </div>
  );
}

export default function UnitDashboard() {
  const navigate = useNavigate();
  const { unitId = "ukucha-03" } = useParams();
  const { t, language } = useLanguage();
  const unit = unitInfo[unitId.toLowerCase()] ?? { name: unitId, zone: "Zona desconocida" };
  const [flyout, setFlyout] = useState<Flyout>(null);
  const [detectionOpen, setDetectionOpen] = useState(false);
  const [sensorsCollapsed, setSensorsCollapsed] = useState(false);
  const cameraRef = useRef<HTMLVideoElement>(null);
  const [cameraStatus, setCameraStatus] = useState<"requesting" | "live" | "offline">("requesting");
  const [pressedKeys, setPressedKeys] = useState({
    w: false,
    a: false,
    s: false,
    d: false,
  });

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.repeat) return;
      const key = e.key.toLowerCase();
      if (key === "w" || key === "a" || key === "s" || key === "d") {
        setPressedKeys((prev) => ({ ...prev, [key]: true }));
      }
    };

    const handleKeyUp = (e: KeyboardEvent) => {
      const key = e.key.toLowerCase();
      if (key === "w" || key === "a" || key === "s" || key === "d") {
        setPressedKeys((prev) => ({ ...prev, [key]: false }));
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("keyup", handleKeyUp);

    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("keyup", handleKeyUp);
    };
  }, []);

  const handleKeyMouseDown = (key: "w" | "a" | "s" | "d") => {
    setPressedKeys((prev) => ({ ...prev, [key]: true }));
  };

  const handleKeyMouseUp = (key: "w" | "a" | "s" | "d") => {
    setPressedKeys((prev) => ({ ...prev, [key]: false }));
  };

  useEffect(() => {
    let stream: MediaStream | undefined;

    if (!navigator.mediaDevices?.getUserMedia) {
      setCameraStatus("offline");
      return;
    }

    navigator.mediaDevices.getUserMedia({ video: true, audio: false })
      .then((cameraStream) => {
        stream = cameraStream;
        setCameraStatus("live");
        if (cameraRef.current) cameraRef.current.srcObject = cameraStream;
      })
      .catch(() => setCameraStatus("offline"));

    return () => {
      stream?.getTracks().forEach((track) => track.stop());
    };
  }, []);

  const openTool = (tool: Exclude<Flyout, null>) => {
    if (window.matchMedia("(max-width: 599px)").matches) {
      navigate(`/${tool}`);
      return;
    }
    setFlyout(flyout === tool ? null : tool);
  };

  return (
    <section className="mission-screen">
      <div className={`mission-stage${sensorsCollapsed ? " sensors-collapsed" : ""}`}>
        <div className="mission-canvas">
          <video ref={cameraRef} className={`unit-camera-feed${cameraStatus === "live" ? " is-live" : ""}`} autoPlay playsInline muted aria-label={`Webcam del Dashboard de ${unit.name}`} />
          <div className="mission-video-texture" aria-hidden="true" />
          {cameraStatus === "offline" && <span className="unit-camera-message">{t("permite_camara")}</span>}
          <button className="yolo-detection" type="button" onClick={() => setDetectionOpen(true)} aria-label={t("detalle_deteccion")}>
            <span className="yolo-detection__corner yolo-detection__corner--tl" />
            <span className="yolo-detection__corner yolo-detection__corner--tr" />
            <span className="yolo-detection__corner yolo-detection__corner--bl" />
            <span className="yolo-detection__corner yolo-detection__corner--br" />
            <span className="yolo-detection__label">{language === "English" ? "PERSON 92%" : "PERSONA 92%"}</span>
          </button>

          <div className="movement-controls">
            <div className="movement-hud" aria-label="HUD de movimiento WASD">
              <div className="movement-hud__row">
                <button
                  type="button"
                  className={`hud-key${pressedKeys.w ? " is-pressed" : ""}`}
                  onMouseDown={() => handleKeyMouseDown("w")}
                  onMouseUp={() => handleKeyMouseUp("w")}
                  onMouseLeave={() => handleKeyMouseUp("w")}
                  onTouchStart={() => handleKeyMouseDown("w")}
                  onTouchEnd={() => handleKeyMouseUp("w")}
                >
                  W
                </button>
              </div>
              <div className="movement-hud__row">
                <button
                  type="button"
                  className={`hud-key${pressedKeys.a ? " is-pressed" : ""}`}
                  onMouseDown={() => handleKeyMouseDown("a")}
                  onMouseUp={() => handleKeyMouseUp("a")}
                  onMouseLeave={() => handleKeyMouseUp("a")}
                  onTouchStart={() => handleKeyMouseDown("a")}
                  onTouchEnd={() => handleKeyMouseUp("a")}
                >
                  A
                </button>
                <button
                  type="button"
                  className={`hud-key${pressedKeys.s ? " is-pressed" : ""}`}
                  onMouseDown={() => handleKeyMouseDown("s")}
                  onMouseUp={() => handleKeyMouseUp("s")}
                  onMouseLeave={() => handleKeyMouseUp("s")}
                  onTouchStart={() => handleKeyMouseDown("s")}
                  onTouchEnd={() => handleKeyMouseUp("s")}
                >
                  S
                </button>
                <button
                  type="button"
                  className={`hud-key${pressedKeys.d ? " is-pressed" : ""}`}
                  onMouseDown={() => handleKeyMouseDown("d")}
                  onMouseUp={() => handleKeyMouseUp("d")}
                  onMouseLeave={() => handleKeyMouseUp("d")}
                  onTouchStart={() => handleKeyMouseDown("d")}
                  onTouchEnd={() => handleKeyMouseUp("d")}
                >
                  D
                </button>
              </div>
            </div>
            <div className="movement-coordinates">
              <strong>{placeholderTelemetry.gps.latitude?.toFixed(5) ?? "N/D"}</strong>
              <strong>{placeholderTelemetry.gps.longitude?.toFixed(5) ?? "N/D"}</strong>
            </div>
          </div>
        </div>
        <div className="unit-dashboard-nav-wrap">
          <nav className="unit-dashboard-nav" aria-label="Controles de unidad">
            <button className="unit-back-button" type="button" onClick={() => navigate(`/unit/${unitId}/sensors`)} aria-label={t("volver_a_sensores")}>{icons.back}</button>
            <div className="unit-dashboard-identity">
              <strong>{unit.name}</strong>
              <span>{t(unit.zone) || unit.zone}</span>
              <b><i /> {t("datos_placeholder")}</b>
            </div>
            <div className="unit-dashboard-actions">
              <button className={flyout === "timeline" ? "is-active" : ""} type="button" onClick={() => openTool("timeline")}>
                {icons.timeline}
                <span>{language === "English" ? "Timeline" : "Timeline"}</span>
              </button>
              <button className={flyout === "copilot" ? "is-active" : ""} type="button" onClick={() => openTool("copilot")}>
                {icons.copilot}
                <span>{t("copiloto_ia")}</span>
              </button>
            </div>
          </nav>
          {flyout && <UnitFlyout type={flyout} onClose={() => setFlyout(null)} />}
        </div>
        <div className="golden-hours golden-hours--mission"><span>GOLDEN HOURS</span><strong>01:42:18</strong></div>
        <aside className={`unit-dashboard-sensors telemetry-deck${sensorsCollapsed ? " is-collapsed" : ""}`}>
          <header className="telemetry-deck__header">
            <div>
              <span>{t("telemetria")}</span>
              <strong>{t("lecturas_campo")}</strong>
            </div>
            {!sensorsCollapsed && <button className="sensor-deck-toggle sensor-deck-toggle--inline" type="button" onClick={() => setSensorsCollapsed(true)} aria-label={language === "English" ? "Hide sensors" : "Ocultar sensores"}><span className="material-symbols-rounded">chevron_right</span></button>}
          </header>
          <ConnectionMetricCard updated={t("actualizado_ahora")} status="demo" />
          <AudioMetricCard left={placeholderTelemetry.audio.left} right={placeholderTelemetry.audio.right} />
          <EnvironmentMetricCard temperature={placeholderTelemetry.environment.temperatureC} humidity={placeholderTelemetry.environment.humidityPercent} />
          <PressureMetricCard pressure={placeholderTelemetry.environment.pressureHpa} />
          <LocationMetricCard latitude={placeholderTelemetry.gps.latitude} longitude={placeholderTelemetry.gps.longitude} valid={placeholderTelemetry.gps.valid} zone={t(unit.zone) || unit.zone} />
        </aside>
        {sensorsCollapsed && <button className="sensor-deck-toggle sensor-deck-toggle--floating" type="button" onClick={() => setSensorsCollapsed(false)} aria-label={language === "English" ? "Show sensors" : "Mostrar sensores"}><span className="material-symbols-rounded">chevron_left</span></button>}
      </div>
      {detectionOpen && (
        <div className="unit-detection-modal-backdrop" role="presentation">
          <section className="unit-detection-modal" role="dialog" aria-modal="true" aria-labelledby="detection-title">
            <header>
              <div>
                <p className="eyebrow">{t("detalle_deteccion")}</p>
                <h2 id="detection-title">{t("persona_confianza")}</h2>
              </div>
              <button type="button" onClick={() => setDetectionOpen(false)} aria-label={t("cerrar")}>{icons.close}</button>
            </header>
            <p>{t("deteccion_capturada", { name: unit.name, zone: t(unit.zone) || unit.zone })}</p>
            <button type="button" onClick={() => setDetectionOpen(false)}>{t("cerrar")}</button>
          </section>
        </div>
      )}
    </section>
  );
}
