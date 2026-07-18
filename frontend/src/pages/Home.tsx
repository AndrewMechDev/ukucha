type Unit = {
  name: string;
  zone: string;
  temperature: string;
  humidity: string;
  activity: string;
  relative: string;
  pressure: string;
  coordinates: string;
  status: "SEGURO" | "PRECAUCIÓN" | "CRÍTICO" | "OFFLINE";
};

const units: Unit[] = [
  {
    name: "Ukucha-01",
    zone: "Zona Norte",
    temperature: "28.4",
    humidity: "34.2 %RH",
    activity: "6.5%",
    relative: "5.6%",
    pressure: "783.1 hPa",
    coordinates: "-16.39880                         -71.53690",
    status: "SEGURO",
  },
  {
    name: "Ukucha-02",
    zone: "Zona Sur",
    temperature: "29.1",
    humidity: "36.8 %RH",
    activity: "12.4%",
    relative: "10.8%",
    pressure: "782.9 hPa",
    coordinates: "-16.39940                         -71.53580",
    status: "PRECAUCIÓN",
  },
  {
    name: "Ukucha-03",
    zone: "Zona Este",
    temperature: "31.7",
    humidity: "42.1 %RH",
    activity: "19.8%",
    relative: "17.4%",
    pressure: "781.6 hPa",
    coordinates: "-16.40110                         -71.53420",
    status: "CRÍTICO",
  },
  {
    name: "Ukucha-04",
    zone: "Zona Oeste",
    temperature: "—",
    humidity: "—",
    activity: "—",
    relative: "—",
    pressure: "—",
    coordinates: "sin señal",
    status: "OFFLINE",
  },
];

function UnitCard({ unit, index }: { unit: Unit; index: number }) {
  const offline = unit.status === "OFFLINE";

  return (
    <article className={`unit-card ${offline ? "is-offline" : ""}`}>
      <header className="unit-card__header">
        <div>
          <span className="eyebrow">UNIDAD DE CAMPO</span>
          <h2>{unit.name}</h2>
          <span className="muted">{unit.zone}</span>
        </div>
        <div className="unit-card__status">
          <strong>{unit.status}</strong>
          <small>hace {index * 13 + 12}s</small>
        </div>
      </header>

      <div className="metrics">
        <section className="metric metric--environment">
          <span className="eyebrow">AMBIENTE <i /></span>
          <b>{unit.temperature}<small> °C</small></b>
          <div className="metric__line" />
          <span className="metric__footer">HUMEDAD <strong>{unit.humidity}</strong></span>
        </section>
        <section className="metric metric--activity">
          <div className="metric__labels">
            <span>ACTIVIDAD<br />ACÚSTICA</span>
            <span>NIVEL<br />RELATIVO</span>
          </div>
          <div className="sparkline" />
          <div className="metric__values"><b>{unit.activity}</b><b>{unit.relative}</b></div>
        </section>
      </div>

      <section className="map-panel">
        <div className="map-panel__title">
          <span className="eyebrow">POSICIÓN</span>
          <span className="fix">{offline ? "SIN SEÑAL" : "FIX VÁLIDO"}</span>
        </div>
        {!offline && <img className="mouse-marker" src="/ukucha-mouse.png" alt={`Ubicación de ${unit.name}`} />}
        <div className="road road--one" />
        <div className="road road--two" />
        <div className="map-route" />
        <span className="map-zone">{unit.zone}</span>
        <div className="coordinates">{unit.coordinates}</div>
      </section>

      <footer className="unit-card__footer">
        <span>PRESIÓN <strong>{unit.pressure}</strong></span>
        <span className="dashboard-link">ABRIR DASHBOARD →</span>
      </footer>
    </article>
  );
}

export default function Home() {
  return (
    <div className="dashboard-shell">
      <aside className="sidebar">
        <div className="brand"><span className="brand-mark">●</span> UKUCHA <span className="collapse">‹</span></div>
        <nav>
          <a className="active" href="/"><span>◇</span> Flota</a>
          <a href="/"><span>♧</span> Alertas <b>3</b></a>
          <a href="/"><span>⚙</span> Ajustes</a>
        </nav>
        <div className="active-count"><i /> N unidades activas</div>
      </aside>
      <main className="dashboard">
        <div className="dashboard__top">
          <div><span className="eyebrow">OPERACIÓN EN CURSO</span><h1>Flota</h1><p>3 unidades activas <span>•</span> 1 en alerta</p></div>
          <button type="button">＋ Vincular unidad</button>
        </div>
        <div className="unit-grid">{units.map((unit, index) => <UnitCard key={unit.name} unit={unit} index={index} />)}</div>
      </main>
    </div>
  );
}
