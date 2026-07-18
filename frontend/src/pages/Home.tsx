import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  UnitSummaryCard,
  type TelemetrySnapshot,
} from "../components/TelemetryCards";
import { useLanguage } from "../components/LanguageContext";
import PwaInstallButton from "../components/PwaInstallButton";

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
  const { t } = useLanguage();
  const zoneLabel = t(unit.zone) || unit.zone;
  const timeFormatted = unit.updated
    .replace("hace", t("hace"))
    .replace("s", t("segundos_abr"))
    .replace("m", t("minutos_abr"));

  return (
    <article
      className={`fleet-unit-card fleet-unit-card--${unit.status}`}
      role={unit.status === "offline" ? undefined : "link"}
      tabIndex={unit.status === "offline" ? -1 : 0}
      onClick={() => onSelect(unit)}
      onKeyDown={(event) => {
        if (unit.status !== "offline" && (event.key === "Enter" || event.key === " ")) onSelect(unit);
      }}
      title={unit.status === "offline" ? t("sin_senal") : `${t("abrir_dashboard").replace(" →", "")} ${unit.id}`}
      aria-label={`${unit.id}, ${t(unit.status)}, ${zoneLabel}`}
    >
      <header className="fleet-unit-card__heading">
        <div>
          <p className="fleet-unit-card__overline">{t("unidad_de_campo")}</p>
          <h2>{unit.id}</h2>
          <span>{zoneLabel}</span>
        </div>
        <div className="fleet-unit-card__status">
          <span className={`fleet-status-tag fleet-status-tag--${unit.status}`}>{t(unit.status)}</span>
          <time>{timeFormatted}</time>
        </div>
      </header>
      <UnitSummaryCard battery={unit.status === "critical" ? 42 : unit.status === "caution" ? 58 : 70} sensorValue={unit.status === "critical" ? "19.6%" : "28.4°C"} sensorLabel={unit.status === "critical" ? "O₂" : "TEMP"} />
      <footer className="fleet-unit-card__footer">
        <span>{t("presion")}</span>
        <strong>{unit.telemetry.environment.pressureHpa === null ? t("sin_datos") : `${unit.telemetry.environment.pressureHpa.toFixed(1)} hPa`}</strong>
        <b>{unit.status === "offline" ? t("sin_datos") : t("abrir_dashboard")}</b>
      </footer>
    </article>
  );
}

function EmptyFleetState({ onLink }: { onLink: () => void }) {
  const { t } = useLanguage();
  return (
    <div className="fleet-empty">
      <div className="fleet-empty__icon">{icons.link}</div>
      <h2>{t("sin_unidades_registradas")}</h2>
      <p>{t("vincula_unidad_desc")}</p>
      <button className="primary-button" type="button" onClick={onLink}>{icons.link}<span>{t("vincular_unidad")}</span></button>
    </div>
  );
}

type LinkStep = "methods" | "scanning" | "results" | "success";

function LinkUnitModal({ onClose }: { onClose: () => void }) {
  const { t, language } = useLanguage();
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
          <header><div><p className="eyebrow">{t("nueva_conexion")}</p><h2 id="scan-title">{t("buscando_ukuchas")}</h2></div><button type="button" onClick={onClose} aria-label="Cerrar modal">{icons.close}</button></header>
          <div className="fleet-scanner" aria-live="polite">
            <div className="fleet-scanner__waves"><span /><span /><span /><b>{icons.wifi}</b></div>
            <strong>{t("escaneando_frecuencias")}</strong>
            <span>{t("buscando_wifi")}</span>
          </div>
        </section>
      </div>
    );
  }

  if (step === "results") {
    return (
      <div className="fleet-modal-backdrop" role="presentation">
        <section className="fleet-modal fleet-modal--results" role="dialog" aria-modal="true" aria-labelledby="results-title">
          <header><div><p className="eyebrow">{t("red_local")}</p><h2 id="results-title">{t("ukuchas_disponibles")}</h2></div><button type="button" onClick={onClose} aria-label="Cerrar modal">{icons.close}</button></header>
          <p className="fleet-modal__description">{t("selecciona_unidad")}</p>
          <div className="fleet-discovered-list">
            <button type="button" className="fleet-discovered-unit" onClick={connectUnit}>
              <span className="fleet-discovered-unit__signal">⌁</span>
              <span>
                <strong>Ukucha-05</strong>
                <small>{language === "English" ? "North Zone · Excellent signal" : "Zona Norte · Señal excelente"}</small>
              </span>
              <b>{t("conectar")} →</b>
            </button>
            <button type="button" className="fleet-discovered-unit" onClick={connectUnit}>
              <span className="fleet-discovered-unit__signal">⌁</span>
              <span>
                <strong>Ukucha-06</strong>
                <small>{language === "English" ? "South Zone · Good signal" : "Zona Sur · Señal buena"}</small>
              </span>
              <b>{t("conectar")} →</b>
            </button>
          </div>
          <button className="secondary-button fleet-rescan" type="button" onClick={() => setStep("scanning")}>↻ {t("buscar_de_nuevo")}</button>
        </section>
      </div>
    );
  }

  if (step === "success") {
    return (
      <div className="fleet-modal-backdrop" role="presentation">
        <section className="fleet-modal fleet-modal--success" role="dialog" aria-modal="true" aria-labelledby="success-title">
          <div className="fleet-success-icon">✓</div>
          <p className="eyebrow">{t("conexion_completada")}</p>
          <h2 id="success-title">{language === "English" ? "Ukucha-05 connected" : "Ukucha-05 conectada"}</h2>
          <p className="fleet-modal__description">{t("unidad_transmitiendo")}</p>
          <button className="primary-button" type="button" onClick={onClose}>{t("ver_unidad")}</button>
        </section>
      </div>
    );
  }

  return (
    <div className="fleet-modal-backdrop" role="presentation">
      <section className="fleet-modal" role="dialog" aria-modal="true" aria-labelledby="link-unit-title">
        <header><div><p className="eyebrow">{t("nueva_conexion")}</p><h2 id="link-unit-title">{t("vincular_nueva_unidad")}</h2></div><button type="button" onClick={onClose} aria-label="Cerrar modal">{icons.close}</button></header>
        <p className="fleet-modal__description">{t("buscar_unidades_desc")}</p>
        <div className="fleet-connection-methods">
          <button type="button" className="fleet-connection-method" onClick={() => setStep("scanning")}><span className="fleet-method-icon">{icons.wifi}</span><span><strong>{t("via_wifi")}</strong><small>{t("detect_auto")}</small></span><b>→</b></button>
          <button type="button" className="fleet-connection-method fleet-connection-method--disabled" disabled><span className="fleet-method-icon">ᛒ</span><span><strong>{t("via_bluetooth")}</strong><small>{t("prox_disponible")}</small></span><b>→</b></button>
        </div>
      </section>
    </div>
  );
}

export default function Home() {
  const navigate = useNavigate();
  const { t } = useLanguage();
  const [modalOpen, setModalOpen] = useState(false);

  const selectUnit = (unit: Unit) => {
    if (unit.status !== "offline") navigate(`/unit/${unit.id.toLowerCase()}/sensors`);
  };

  return (
    <section className="fleet-screen">
      <header className="fleet-header">
        <div>
          <p className="eyebrow">{t("operacion_en_curso")}</p>
          <h1>{t("flota")}</h1>
          <p className="fleet-summary"><strong>3</strong> {t("unidades_activas")} · <strong>1</strong> {t("en_alerta")}</p>
        </div>
        <div className="fleet-header__actions">
          <PwaInstallButton collapsed={false} />
          <button className="primary-button fleet-link-button" type="button" onClick={() => setModalOpen(true)}>{icons.plus}<span>{t("vincular_unidad")}</span></button>
        </div>
      </header>
      <div className="fleet-grid" aria-label="Unidades de la flota">
        {units.map((unit) => <UnitCard unit={unit} onSelect={selectUnit} key={unit.id} />)}
      </div>
      {modalOpen && <LinkUnitModal onClose={() => setModalOpen(false)} />}
    </section>
  );
}

export { EmptyFleetState };
