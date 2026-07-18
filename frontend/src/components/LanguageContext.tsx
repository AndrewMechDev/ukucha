import { createContext, useContext, useState, type ReactNode } from "react";

export type Language = "Español" | "English";

type LanguageContextType = {
  language: Language;
  setLanguage: (lang: Language) => void;
  t: (key: string, replacements?: Record<string, string>) => string;
};

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export const translations = {
  es: {
    // Sidebar
    "flota": "Flota",
    "alertas": "Alertas",
    "ajustes": "Ajustes",
    "unidades_activas": "unidades activas",
    "unidades_activas_singular": "unidad activa",
    "en_alerta": "en alerta",
    
    // Home Dashboard
    "operacion_en_curso": "OPERACIÓN EN CURSO",
    "vincular_unidad": "Vincular unidad",
    "unidad_de_campo": "UNIDAD DE CAMPO",
    "hace": "hace",
    "segundos_abr": "s",
    "minutos_abr": "m",
    "horas_abr": "h",
    "ambiente": "AMBIENTE",
    "humedad": "HUMEDAD",
    "actividad_acustica": "ACTIVIDAD ACÚSTICA",
    "nivel_relativo": "NIVEL RELATIVO",
    "posicion": "POSICIÓN",
    "sin_senal": "SIN SEÑAL",
    "fix_valido": "FIX VÁLIDO",
    "presion": "PRESIÓN",
    "abrir_dashboard": "ABRIR DASHBOARD →",
    "sin_unidades_registradas": "Sin unidades registradas",
    "vincula_unidad_desc": "Vincula una unidad para comenzar a monitorear tu flota.",
    "nueva_conexion": "NUEVA CONEXIÓN",
    "buscando_ukuchas": "Buscando Ukuchas",
    "escaneando_frecuencias": "Escaneando frecuencias de telemetría...",
    "buscando_wifi": "Buscando unidades disponibles en tu red Wi‑Fi",
    "red_local": "RED LOCAL",
    "ukuchas_disponibles": "Ukuchas disponibles",
    "selecciona_unidad": "Selecciona una unidad para conectarla a tu flota.",
    "conectar": "Conectar",
    "buscar_de_nuevo": "Buscar de nuevo",
    "conexion_completada": "CONEXIÓN COMPLETADA",
    "ukucha_conectada": "Ukucha-05 conectada",
    "unidad_transmitiendo": "La unidad ya está transmitiendo datos en tu red Wi‑Fi.",
    "ver_unidad": "Ver unidad",
    "vincular_nueva_unidad": "Vincular Nueva Unidad",
    "buscar_unidades_desc": "Busca las unidades disponibles en tu red local para añadirlas a la flota.",
    "via_wifi": "Vía Wi‑Fi",
    "detect_auto": "Detección automática en la red local",
    "via_bluetooth": "Vía Bluetooth",
    "prox_disponible": "Próximamente disponible",
    "opciones": "Opciones",
    "sin_datos": "SIN DATOS",
    
    // Statuses
    "SEGURO": "SEGURO",
    "PRECAUCIÓN": "PRECAUCIÓN",
    "CRÍTICO": "CRÍTICO",
    "OFFLINE": "OFFLINE",
    "safe": "Seguro",
    "caution": "Precaución",
    "critical": "Crítico",
    "offline": "Offline",

    // Settings Modal
    "configuracion_del_sistema": "CONFIGURACIÓN DEL SISTEMA",
    "apariencia": "Apariencia",
    "tema": "Tema",
    "pref_contraste": "Preferencia de contraste de la interfaz",
    "claro": "Claro",
    "oscuro": "Oscuro",
    "general": "General",
    "operacion": "Operación",
    "normativa": "Normativa",
    "idioma": "Idioma",
    "acerca_de": "Acerca de",
    "unidades_de_medida": "Unidades de medida",
    "sistema": "Sistema",
    "formato_distancias": "Formato para distancias y lecturas",
    "metrico": "Métrico",
    "imperial": "Imperial",
    "umbrales_normativos": "Umbrales normativos de referencia (D.S. 024-2016-EM)",
    "solo_referencia": "Solo referencia — no editable en esta versión",
    "idioma_interfaz": "Idioma de la interfaz y mensajes del sistema",
    "acerca_desc": "Ukucha — asistencia SAR inspirada en la biomímesis y el trabajo de APOPO.",
    "build_hackathon": "Build de hackathon",

    // Unit Dashboard / Camera
    "live_webcam": "LIVE · WEBCAM",
    "sin_senal_webcam": "SIN SEÑAL · WEBCAM",
    "permite_camara": "Permite el acceso a la cámara para ver el feed en vivo.",
    "persona_detectada": "Persona detectada",
    "alerta_de_gas": "Alerta de gas",
    "reconexion": "Reconexión",
    "copiloto_ia": "Copiloto IA",
    "preguntar_copiloto": "Preguntar al copiloto...",
    "datos_placeholder": "Datos placeholder",
    "video": "Video",
    "mapa": "Mapa",
    "timeline_eventos": "Timeline de eventos",
    "telemetria": "TELEMETRÍA",
    "lecturas_campo": "Lecturas de campo",
    "estado_de_datos": "ESTADO DE DATOS",
    "muestra_simulada": "MUESTRA SIMULADA",
    "actualizado_ahora": "actualizado ahora",
    "volver_a_sensores": "Volver a sensores",
    "detalle_deteccion": "DETALLE DE DETECCIÓN",
    "persona_confianza": "Persona · confianza 92%",
    "deteccion_capturada": "Detección capturada por {name} en {zone}.",
    "cerrar": "Cerrar",

    // Sensors Page
    "sensores": "Sensores",
    "telemetria_unidad": "Telemetría en tiempo real",
    "volver_a_flota": "Volver a flota",
    "panel_de_control": "Panel de control",
    "transmision_voz": "Transmisión de voz (TTS)",
    "enviar_audio": "Enviar audio",
    "escribe_mensaje": "Escribe un mensaje para reproducir en la unidad...",
    "historial_alertas": "Historial de Alertas",
  },
  en: {
    // Sidebar
    "flota": "Fleet",
    "alertas": "Alerts",
    "ajustes": "Settings",
    "unidades_activas": "active units",
    "unidades_activas_singular": "active unit",
    "en_alerta": "in alert",

    // Home Dashboard
    "operacion_en_curso": "OPERATION IN PROGRESS",
    "vincular_unidad": "Link unit",
    "unidad_de_campo": "FIELD UNIT",
    "hace": "ago",
    "segundos_abr": "s",
    "minutos_abr": "m",
    "horas_abr": "h",
    "ambiente": "ENVIRONMENT",
    "humedad": "HUMIDITY",
    "actividad_acustica": "ACOUSTIC ACTIVITY",
    "nivel_relativo": "RELATIVE LEVEL",
    "posicion": "POSITION",
    "sin_senal": "NO SIGNAL",
    "fix_valido": "VALID FIX",
    "presion": "PRESSURE",
    "abrir_dashboard": "OPEN DASHBOARD →",
    "sin_unidades_registradas": "No units registered",
    "vincula_unidad_desc": "Link a unit to start monitoring your fleet.",
    "nueva_conexion": "NEW CONNECTION",
    "buscando_ukuchas": "Searching for Ukuchas",
    "escaneando_frecuencias": "Scanning telemetry frequencies...",
    "buscando_wifi": "Searching for available units on your Wi‑Fi network",
    "red_local": "LOCAL NETWORK",
    "ukuchas_disponibles": "Available Ukuchas",
    "selecciona_unidad": "Select a unit to connect it to your fleet.",
    "conectar": "Connect",
    "buscar_de_nuevo": "Search again",
    "conexion_completada": "CONNECTION COMPLETED",
    "ukucha_conectada": "Ukucha-05 connected",
    "unidad_transmitiendo": "The unit is now transmitting data on your Wi‑Fi network.",
    "ver_unidad": "View unit",
    "vincular_nueva_unidad": "Link New Unit",
    "buscar_unidades_desc": "Search for available units on your local network to add them to the fleet.",
    "via_wifi": "Via Wi‑Fi",
    "detect_auto": "Automatic detection on the local network",
    "via_bluetooth": "Via Bluetooth",
    "prox_disponible": "Coming soon",
    "opciones": "Options",
    "sin_datos": "NO DATA",

    // Statuses
    "SEGURO": "SAFE",
    "PRECAUCIÓN": "WARNING",
    "CRÍTICO": "CRITICAL",
    "OFFLINE": "OFFLINE",
    "safe": "Safe",
    "caution": "Warning",
    "critical": "Critical",
    "offline": "Offline",

    // Settings Modal
    "configuracion_del_sistema": "SYSTEM CONFIGURATION",
    "apariencia": "Appearance",
    "tema": "Theme",
    "pref_contraste": "Interface contrast preference",
    "claro": "Light",
    "oscuro": "Dark",
    "general": "General",
    "operacion": "Operation",
    "normativa": "Thresholds",
    "idioma": "Language",
    "acerca_de": "About",
    "unidades_de_medida": "Units of measure",
    "sistema": "System",
    "formato_distancias": "Format for distances and readings",
    "metrico": "Metric",
    "imperial": "Imperial",
    "umbrales_normativos": "Regulatory reference thresholds (D.S. 024-2016-EM)",
    "solo_referencia": "Reference only — not editable in this version",
    "idioma_interfaz": "Interface language and system messages",
    "acerca_desc": "Ukucha — SAR assistance inspired by biomimicry and the work of APOPO.",
    "build_hackathon": "Hackathon build",

    // Unit Dashboard / Camera
    "live_webcam": "LIVE · WEBCAM",
    "sin_senal_webcam": "NO SIGNAL · WEBCAM",
    "permite_camara": "Allow camera access to view the live feed.",
    "persona_detectada": "Person detected",
    "alerta_de_gas": "Gas alert",
    "reconexion": "Reconnection",
    "copiloto_ia": "AI Copilot",
    "preguntar_copiloto": "Ask copilot...",
    "datos_placeholder": "Placeholder data",
    "video": "Video",
    "mapa": "Map",
    "timeline_eventos": "Event timeline",
    "telemetria": "TELEMETRY",
    "lecturas_campo": "Field readings",
    "estado_de_datos": "DATA STATE",
    "muestra_simulada": "SIMULATED SAMPLE",
    "actualizado_ahora": "updated now",
    "volver_a_sensores": "Back to sensors",
    "detalle_deteccion": "DETECTION DETAILS",
    "persona_confianza": "Person · confidence 92%",
    "deteccion_capturada": "Detection captured by {name} in {zone}.",
    "cerrar": "Close",

    // Sensors Page
    "sensores": "Sensors",
    "telemetria_unidad": "Real-time telemetry",
    "volver_a_flota": "Back to fleet",
    "panel_de_control": "Control panel",
    "transmision_voz": "Voice transmission (TTS)",
    "enviar_audio": "Send audio",
    "escribe_mensaje": "Write a message to play on the unit...",
    "historial_alertas": "Alert History",
  }
};

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<Language>(() => {
    const saved = localStorage.getItem("language");
    return saved === "English" ? "English" : "Español";
  });

  const setLanguage = (lang: Language) => {
    setLanguageState(lang);
    localStorage.setItem("language", lang);
  };

  const t = (key: string, replacements?: Record<string, string>) => {
    const langCode = language === "English" ? "en" : "es";
    const dict = translations[langCode];
    let text = dict[key as keyof typeof dict] || key;
    if (replacements) {
      Object.entries(replacements).forEach(([k, v]) => {
        text = text.replace(`{${k}}`, v);
      });
    }
    return text;
  };

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error("useLanguage must be used within a LanguageProvider");
  }
  return context;
}
