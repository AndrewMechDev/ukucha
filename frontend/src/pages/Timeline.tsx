import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

type EventCategory = "detección" | "alerta" | "sistema";
type Filter = "Todos" | "Detecciones" | "Alertas" | "Sistema";

type TimelineEvent = {
  id: number;
  category: EventCategory;
  description: string;
  timestamp: string;
  severity?: "safe" | "caution" | "critical";
};

const events: TimelineEvent[] = [
  { id: 1, category: "detección", description: "Persona detectada · confianza 92%", timestamp: "14:32:07" },
  { id: 2, category: "alerta", description: "O₂ bajo el límite normativo", timestamp: "14:31:42", severity: "critical" },
  { id: 3, category: "sistema", description: "Telemetría sincronizada con la unidad", timestamp: "14:30:18" },
  { id: 4, category: "detección", description: "Movimiento detectado en Zona Norte", timestamp: "14:28:56" },
  { id: 5, category: "alerta", description: "Nivel de gas CO en umbral de precaución", timestamp: "14:26:21", severity: "caution" },
  { id: 6, category: "sistema", description: "Reconexión de WebSocket", timestamp: "14:19:04" },
  { id: 7, category: "detección", description: "Objeto identificado · confianza 78%", timestamp: "14:16:43" },
  { id: 8, category: "alerta", description: "Batería de robot por debajo del 25%", timestamp: "14:11:09", severity: "caution" },
];

const filters: Filter[] = ["Todos", "Detecciones", "Alertas", "Sistema"];

const icons = {
  detection: <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="4" /><path d="M3 12s3-6 9-6 9 6 9 6-3 6-9 6-9-6-9-6ZM5 5l2 2M19 5l-2 2M5 19l2-2M19 19l-2-2" /></svg>,
  alert: <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m12 3 9 17H3L12 3Z" /><path d="M12 9v4M12 17h.01" /></svg>,
  system: <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M18.4 5.6l-2.1 2.1M7.7 16.3l-2.1 2.1" /><circle cx="12" cy="12" r="4" /></svg>,
  close: <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18" /></svg>,
};

function eventIcon(category: EventCategory) {
  if (category === "detección") return icons.detection;
  if (category === "alerta") return icons.alert;
  return icons.system;
}

function matchesFilter(category: EventCategory, filter: Filter) {
  return filter === "Todos" || (filter === "Detecciones" && category === "detección") || (filter === "Alertas" && category === "alerta") || (filter === "Sistema" && category === "sistema");
}

export function EmptyTimeline() {
  return <div className="timeline-empty"><p>Sin eventos registrados todavía</p></div>;
}

export default function Timeline() {
  const navigate = useNavigate();
  const [filter, setFilter] = useState<Filter>("Todos");
  const [openDetection, setOpenDetection] = useState<number | null>(null);
  const visibleEvents = useMemo(() => events.filter((event) => matchesFilter(event.category, filter)), [filter]);

  return (
    <div className="timeline-mobile-screen">
      <div className="timeline-mobile-sheet">
        <div className="timeline-drag-handle" aria-hidden="true" />
        <header className="timeline-mobile-header">
          <div><p className="eyebrow">REGISTRO DE ACTIVIDAD</p><h1>Timeline <span>· Ukucha-03</span></h1></div>
          <button type="button" className="timeline-close" onClick={() => navigate(-1)} aria-label="Cerrar Timeline">{icons.close}</button>
        </header>
        <div className="timeline-filters" role="tablist" aria-label="Filtrar eventos">
          {filters.map((item) => <button className={filter === item ? "is-selected" : ""} type="button" role="tab" aria-selected={filter === item} onClick={() => setFilter(item)} key={item}>{item}</button>)}
        </div>
        {visibleEvents.length === 0 ? <EmptyTimeline /> : <div className="timeline-events" aria-label="Eventos de Ukucha-03">
          {visibleEvents.map((event) => (
            <button className={`timeline-event timeline-event--${event.category}${event.severity ? ` timeline-event--${event.severity}` : ""}`} type="button" key={event.id} onClick={() => event.category === "detección" && setOpenDetection(event.id)} aria-label={event.category === "detección" ? `${event.description}, abrir detalle` : event.description}>
              <span className="timeline-event__icon">{eventIcon(event.category)}</span>
              <span className="timeline-event__description">{event.description}</span>
              <time>{event.timestamp}</time>
              {event.category === "detección" && <span className="timeline-event__chevron" aria-hidden="true">›</span>}
            </button>
          ))}
        </div>}
      </div>
      {openDetection !== null && <div className="timeline-detection-note" role="status">Detalle de detección disponible</div>}
    </div>
  );
}
