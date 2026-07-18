import { useNavigate, useParams } from "react-router-dom";
import {
  AudioMetricCard,
  EnvironmentMetricCard,
  LocationMetricCard,
  PressureMetricCard,
} from "../components/TelemetryCards";

const units: Record<string, { name: string; zone: string }> = {
  "ukucha-01": { name: "Ukucha-01", zone: "Zona Norte" },
  "ukucha-02": { name: "Ukucha-02", zone: "Zona Sur" },
  "ukucha-03": { name: "Ukucha-03", zone: "Zona Este" },
  "ukucha-04": { name: "Ukucha-04", zone: "Zona Oeste" },
};

export default function UnitSensors() {
  const navigate = useNavigate();
  const { unitId = "ukucha-01" } = useParams();
  const unit = units[unitId.toLowerCase()] ?? { name: unitId, zone: "Zona desconocida" };

  return (
    <section className="sensor-page">
      <header className="sensor-page__header">
        <div>
          <button className="sensor-page__back" type="button" onClick={() => navigate("/")} aria-label="Volver a Flota">← Flota</button>
          <p className="eyebrow">DATOS DE LA UNIDAD</p>
          <h1>{unit.name} <span>· {unit.zone}</span></h1>
          <p>Lecturas completas y estado de todos los sensores.</p>
        </div>
        <button className="sensor-page__camera-button" type="button" onClick={() => navigate(`/unit/${unitId}`)}>
          <span className="material-symbols-rounded">videocam</span>
          Abrir panel de cámara
        </button>
      </header>

      <div className="sensor-page__grid">
        <AudioMetricCard left={6.5} right={5.6} />
        <EnvironmentMetricCard temperature={28.4} humidity={34.2} />
        <PressureMetricCard pressure={783.1} />
        <LocationMetricCard latitude={-16.3988} longitude={-71.5369} valid zone={unit.zone} />
        <article className="telemetry-card sensor-data-card"><span className="telemetry-card__label">OXÍGENO (O₂)</span><strong>19.6 <small>%</small></strong><b className="sensor-warning">Bajo el límite</b></article>
        <article className="telemetry-card sensor-data-card"><span className="telemetry-card__label">MONÓXIDO DE CARBONO (CO)</span><strong>12 <small>ppm</small></strong><b>Normal</b></article>
        <article className="telemetry-card sensor-data-card"><span className="telemetry-card__label">HUMEDAD DEL TERRENO</span><strong>41 <small>%</small></strong><b>Normal</b></article>
        <article className="telemetry-card sensor-data-card"><span className="telemetry-card__label">SEÑAL TETHER</span><strong>-62 <small>dBm</small></strong><b>Buena</b></article>
        <article className="telemetry-card sensor-data-card"><span className="telemetry-card__label">TEMPERATURA DEL MOTOR</span><strong>42 <small>°C</small></strong><b>Normal</b></article>
        <article className="telemetry-card sensor-data-card"><span className="telemetry-card__label">VELOCIDAD</span><strong>1.8 <small>m/s</small></strong><b>En movimiento</b></article>
      </div>
    </section>
  );
}
