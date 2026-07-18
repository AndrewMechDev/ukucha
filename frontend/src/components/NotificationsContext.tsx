import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { useUnitStream } from "../hooks/useUnitStream";

export type NotificationSeverity = "critical" | "caution";

export type AppNotification = {
  id: number;
  tipo: string;
  severity: NotificationSeverity;
  unit: string;
  zone: string;
  description: string;
  timestamp: string;
  acknowledged: boolean;
  count: number;
};

type NotificationsContextValue = {
  notifications: AppNotification[];
  unacknowledgedCount: number;
  acknowledge: (id: number) => void;
};

const NotificationsContext = createContext<NotificationsContextValue | null>(null);

// Solo hay un robot real conectado hoy (esp32s3_campo) -- se etiqueta con
// la misma identidad que ya usa UnitDashboard para esa unidad, no se
// inventan alertas de una flota de 4 que no existe fisicamente.
const REAL_UNIT = { name: "Ukucha-01", zone: "Zona Norte" };

const PERSON_DETECTED_MAX_PER_WINDOW = 3;
const PERSON_DETECTED_WINDOW_MS = 60_000;
const MAX_NOTIFICATIONS = 50;

type EdgeState = {
  alerta: boolean;
  critica: boolean;
  rubble: boolean;
  pir: boolean;
  stale: boolean;
};

const initialEdgeState: EdgeState = {
  alerta: false,
  critica: false,
  rubble: false,
  pir: false,
  stale: false,
};

/** Deriva notificaciones reales de deteccion de flanco (false->true) sobre
 * cada EnrichedFrameOutput de /ws/stream -- la misma logica que ya corre
 * en backend/services/event_detector.py, replicada del lado del cliente
 * para no tener que exponer una tabla/endpoint nuevo del backend. */
export function NotificationsProvider({ children }: { children: ReactNode }) {
  const { data: frame } = useUnitStream();
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const idCounter = useRef(0);
  const edgeState = useRef<EdgeState>({ ...initialEdgeState });
  const personDetectedTimestamps = useRef<number[]>([]);

  useEffect(() => {
    if (!frame) return;

    const push = (tipo: string, severity: NotificationSeverity, description: string) => {
      idCounter.current += 1;
      const entry: AppNotification = {
        id: idCounter.current,
        tipo,
        severity,
        unit: REAL_UNIT.name,
        zone: REAL_UNIT.zone,
        description,
        timestamp: frame.timestamp,
        acknowledged: false,
        count: 1,
      };
      setNotifications((list) => [entry, ...list].slice(0, MAX_NOTIFICATIONS));
    };

    // Rate limit: maximo 3 "persona detectada" por minuto -- las que
    // excedan la ventana se acumulan en la ultima notificacion en vez de
    // saturar el dashboard con una fila nueva por cada una.
    const pushPersonDetected = (description: string) => {
      const now = Date.now();
      const recent = personDetectedTimestamps.current.filter(
        (t) => now - t < PERSON_DETECTED_WINDOW_MS,
      );
      if (recent.length >= PERSON_DETECTED_MAX_PER_WINDOW) {
        setNotifications((list) => {
          if (list.length === 0 || list[0].tipo !== "caida_detectada") return list;
          const [head, ...rest] = list;
          return [{ ...head, count: head.count + 1, timestamp: frame.timestamp }, ...rest];
        });
        return;
      }
      recent.push(now);
      personDetectedTimestamps.current = recent;
      push("caida_detectada", "critical", description);
    };

    const prev = edgeState.current;

    if (frame.fall.hay_critica && !prev.critica) {
      push("caida_critica", "critical", "Persona en el suelo por tiempo prolongado");
    }
    if (frame.fall.hay_alerta && !prev.alerta) {
      pushPersonDetected(`Persona detectada · ${frame.fall.n_personas} persona(s)`);
    }
    const rubbleNow = frame.fusion.n_rubble_victims > 0;
    if (rubbleNow && !prev.rubble) {
      push(
        "persona_bajo_escombros",
        "critical",
        `${frame.fusion.n_rubble_victims} victima(s) bajo escombros`,
      );
    }
    const pirNow = frame.env.pir_detected ?? false;
    if (pirNow && !prev.pir) {
      push("movimiento_detectado", "caution", "Movimiento detectado por el sensor PIR");
    }
    const staleNow = frame.audio.stale || frame.env.stale;
    if (staleNow && !prev.stale) {
      push("senal_debil", "caution", "Datos de telemetria atrasados o enlace inestable");
    }

    edgeState.current = {
      alerta: frame.fall.hay_alerta,
      critica: frame.fall.hay_critica,
      rubble: rubbleNow,
      pir: pirNow,
      stale: staleNow,
    };
  }, [frame]);

  const acknowledge = (id: number) => {
    setNotifications((list) =>
      list.map((notification) => (notification.id === id ? { ...notification, acknowledged: true } : notification)),
    );
  };

  const unacknowledgedCount = notifications.filter((n) => !n.acknowledged).length;

  return (
    <NotificationsContext.Provider value={{ notifications, unacknowledgedCount, acknowledge }}>
      {children}
    </NotificationsContext.Provider>
  );
}

export function useNotifications(): NotificationsContextValue {
  const ctx = useContext(NotificationsContext);
  if (!ctx) throw new Error("useNotifications debe usarse dentro de NotificationsProvider");
  return ctx;
}
