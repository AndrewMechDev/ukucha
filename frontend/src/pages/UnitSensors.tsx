import { useNavigate, useParams } from "react-router-dom";
import {
  AudioMetricCard,
  EnvironmentMetricCard,
  LocationMetricCard,
  PressureMetricCard,
} from "../components/TelemetryCards";
import { useUnitStream } from "../hooks/useUnitStream";

const units: Record<string, { name: string; zone: string }> = {
  "ukucha-01": { name: "Ukucha-01", zone: "Zona Norte" },
  "ukucha-02": { name: "Ukucha-02", zone: "Zona Sur" },
  "ukucha-03": { name: "Ukucha-03", zone: "Zona Este" },
  "ukucha-04": { name: "Ukucha-04", zone: "Zona Oeste" },
};

function valueOrPlaceholder(value: number | null, digits = 0) {
  return value === null ? "N/D" : value.toFixed(digits);
}

export default function UnitSensors() {
  const navigate = useNavigate();
  const { unitId = "ukucha-01" } = useParams();
  const unit = units[unitId.toLowerCase()] ?? { name: unitId, zone: "Zona desconocida" };
  const { data: frame } = useUnitStream();

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
        <AudioMetricCard left={frame?.audio.vol_l ?? null} right={frame?.audio.vol_r ?? null} />
        <EnvironmentMetricCard temperature={frame?.env.climate?.temp_c ?? null} humidity={frame?.env.climate?.humidity_pct ?? null} />
        <PressureMetricCard pressure={frame?.env.climate?.pressure_hpa ?? null} />
        <LocationMetricCard
          latitude={frame?.env.gps?.lat ?? null}
          longitude={frame?.env.gps?.lon ?? null}
          valid={Boolean(frame?.env.gps?.lat && frame?.env.gps?.lon)}
          zone={unit.zone}
        />
        <article className="telemetry-card sensor-data-card">
          <span className="telemetry-card__label">GAS MQ7 (CO)</span>
          <strong>{valueOrPlaceholder(frame?.env.gas?.mq1 ?? null, 1)} <small>ADC</small></strong>
          <b>Nivel relativo, sin calibrar a ppm</b>
        </article>
        <article className="telemetry-card sensor-data-card">
          <span className="telemetry-card__label">GAS MQ136 (H₂S)</span>
          <strong>{valueOrPlaceholder(frame?.env.gas?.mq2 ?? null, 1)} <small>ADC</small></strong>
          <b>Nivel relativo, sin calibrar a ppm</b>
        </article>
        <article className="telemetry-card sensor-data-card">
          <span className="telemetry-card__label">PRESENCIA (PIR)</span>
          <strong>{frame?.env.pir_detected ? "Detectado" : "Sin detección"}</strong>
          <b className={frame?.env.pir_detected ? "sensor-warning" : ""}>{frame?.env.pir_detected ? "Movimiento activo" : "Normal"}</b>
        </article>
      </div>
    </section>
  );
}
