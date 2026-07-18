import { useEffect, useState } from "react";
import { apiGet } from "../services/api";

type HealthStatus = {
  status: string;
};

export default function Home() {
  const [status, setStatus] = useState<string>("conectando...");

  useEffect(() => {
    apiGet<HealthStatus>("/v1/health")
      .then((data) => setStatus(data.status))
      .catch(() => setStatus("error de conexión"));
  }, []);

  return (
    <section className="dashboard">
      <header className="dashboard__header">
        <div>
          <p className="eyebrow">OPERACIÓN EN CURSO</p>
          <h1>Flota</h1>
        </div>
        <span className={`api-status${status === "error de conexión" ? " api-status--error" : ""}`}>
          <span aria-hidden="true" />
          API: {status}
        </span>
      </header>

      <div className="fleet-grid" aria-label="Resumen de flota">
        {["UKUCHA-01", "UKUCHA-02", "UKUCHA-03"].map((unit, index) => (
          <article className="instrument-card" key={unit}>
            <div className="instrument-card__top">
              <span className="unit-tag">
                <span aria-hidden="true" /> {unit}
              </span>
              <span className="telemetry-small">ACTIVA</span>
            </div>
            <div>
              <p className="instrument-card__label">AUTONOMÍA</p>
              <p className="instrument-card__value">{31 - index * 6}h</p>
            </div>
            <div className="charge-segments" aria-label={`${70 - index * 10}% de carga`}>
              {Array.from({ length: 10 }, (_, segment) => (
                <span className={segment < 7 - index ? "is-filled" : ""} key={segment} />
              ))}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
