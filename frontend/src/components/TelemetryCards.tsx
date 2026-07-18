import mousePositionImage from "../../raton_posicion.png";

export type TelemetrySnapshot = {
  audio: { left: number | null; right: number | null };
  environment: {
    temperatureC: number | null;
    humidityPercent: number | null;
    pressureHpa: number | null;
  };
  gps: {
    latitude: number | null;
    longitude: number | null;
    valid: boolean;
  };
};

type CardSize = "compact" | "regular";

const waveformPoints = "0,28 10,22 20,34 30,14 40,26 50,18 60,37 70,23 80,31 90,11 100,27 110,19 120,33 130,17 140,25 150,13 160,29";

function valueOrPlaceholder(value: number | null, digits = 1) {
  return value === null ? "N/D" : value.toFixed(digits);
}

export function AudioMetricCard({
  left,
  right,
  size = "regular",
}: {
  left: number | null;
  right: number | null;
  size?: CardSize;
}) {
  const hasSample = left !== null || right !== null;

  return (
    <article className={`telemetry-card audio-metric-card telemetry-card--${size}`}>
      <header>
        <span className="telemetry-card__label">ACTIVIDAD ACÚSTICA</span>
        <span className="telemetry-card__tag">{hasSample ? "NIVEL RELATIVO" : "SIN MUESTRA"}</span>
      </header>
      <svg className="audio-waveform" viewBox="0 0 160 48" preserveAspectRatio="none" aria-hidden="true">
        {hasSample ? <polyline points={waveformPoints} /> : <line className="audio-waveform__empty" x1="0" y1="24" x2="160" y2="24" />}
      </svg>
      <div className="audio-metric-card__values">
        <span><b>L</b><strong>{valueOrPlaceholder(left)}%</strong></span>
        <span><b>R</b><strong>{valueOrPlaceholder(right)}%</strong></span>
      </div>
    </article>
  );
}

export function EnvironmentMetricCard({
  temperature,
  humidity,
  size = "regular",
}: {
  temperature: number | null;
  humidity: number | null;
  size?: CardSize;
}) {
  const hasReading = temperature !== null || humidity !== null;

  return (
    <article className={`telemetry-card environment-metric-card telemetry-card--${size}`}>
      <header>
        <span className="telemetry-card__label">AMBIENTE</span>
        <span className={`telemetry-card__status-dot${hasReading ? "" : " is-offline"}`} aria-label={hasReading ? "Lectura disponible" : "Lectura no disponible"} />
      </header>
      <p className="telemetry-card__hero">{valueOrPlaceholder(temperature)}<small>°C</small></p>
      <footer>
        <span>HUMEDAD</span>
        <strong>{valueOrPlaceholder(humidity)} %RH</strong>
      </footer>
    </article>
  );
}

export function PressureMetricCard({
  pressure,
  size = "regular",
}: {
  pressure: number | null;
  size?: CardSize;
}) {
  return (
    <article className={`telemetry-card pressure-metric-card telemetry-card--${size}`}>
      <header>
        <span className="telemetry-card__label">PRESIÓN</span>
        <span className="telemetry-card__tag">BMP280</span>
      </header>
      <p className="telemetry-card__hero">{valueOrPlaceholder(pressure)}<small>hPa</small></p>
      <div className={`pressure-scale${pressure === null ? " is-unavailable" : ""}`} aria-hidden="true">
        {Array.from({ length: 10 }, (_, index) => <span className={pressure !== null && index < 7 ? "is-active" : ""} key={index} />)}
      </div>
      <p className="telemetry-card__caption">LECTURA BAROMÉTRICA</p>
    </article>
  );
}

export function LocationMetricCard({
  latitude,
  longitude,
  valid,
  zone,
  size = "regular",
}: {
  latitude: number | null;
  longitude: number | null;
  valid: boolean;
  zone: string;
  size?: CardSize;
}) {
  return (
    <article className={`telemetry-card location-metric-card telemetry-card--${size}`}>
      <header>
        <span className="telemetry-card__label">POSICIÓN</span>
        <span className={`telemetry-card__tag${valid ? " is-safe" : " is-offline"}`}>{valid ? "FIX VÁLIDO" : "SIN FIX"}</span>
      </header>
      <div className="location-map-preview" aria-label={valid ? `Posición estimada en ${zone}` : "Posición GPS no disponible"}>
        <svg viewBox="0 0 240 128" preserveAspectRatio="none" aria-hidden="true">
          <path className="map-road map-road--one" d="M-10 106 C35 78 42 26 94 18 S168 65 250 28" />
          <path className="map-road map-road--two" d="M36 -10 C72 38 116 54 112 138" />
          <path className="map-route-preview" d="M28 104 C62 91 69 57 101 62 S143 88 185 43" />
        </svg>
        {valid && <img className="location-map-preview__pin" src={mousePositionImage} alt={`Ubicación de ${zone}`} />}
        <span className="location-map-preview__zone">{zone}</span>
      </div>
      <footer className="location-metric-card__coords">
        <span>{valid && latitude !== null ? latitude.toFixed(5) : "N/D"}</span>
        <span>{valid && longitude !== null ? longitude.toFixed(5) : "N/D"}</span>
      </footer>
    </article>
  );
}

export function ConnectionMetricCard({
  updated,
  status = "demo",
}: {
  updated: string;
  status?: "online" | "stale" | "offline" | "demo";
}) {
  const labels = {
    online: "EN VIVO",
    stale: "DATOS ATRASADOS",
    offline: "SIN CONEXIÓN",
    demo: "MUESTRA SIMULADA",
  };

  return (
    <article className={`telemetry-card connection-metric-card connection-metric-card--${status}`}>
      <span className="connection-metric-card__pulse" aria-hidden="true" />
      <div>
        <span className="telemetry-card__label">ESTADO DE DATOS</span>
        <strong>{labels[status]}</strong>
      </div>
      <time>{updated}</time>
    </article>
  );
}
