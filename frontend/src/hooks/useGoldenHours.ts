import { useEffect, useState } from "react";

const GOLDEN_HOURS_MS = 72 * 60 * 60 * 1000;
const STORAGE_PREFIX = "ukucha:golden-hours-start:";

function loadStart(unitId: string): number {
  const key = STORAGE_PREFIX + unitId;
  const stored = window.localStorage.getItem(key);
  if (stored) return Number(stored);
  const now = Date.now();
  window.localStorage.setItem(key, String(now));
  return now;
}

function formatRemaining(ms: number): string {
  const clamped = Math.max(0, ms);
  const totalSeconds = Math.floor(clamped / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${pad(hours)}:${pad(minutes)}:${pad(seconds)}`;
}

/** Cuenta regresiva de las "72 horas de oro" de SAR para encontrar a una
 * persona, contadas desde la primera vez que se abrio el dashboard de esta
 * unidad (persistido en localStorage para sobrevivir a un refresh). No hay
 * todavia un timestamp de "inicio de mision" real del lado del backend --
 * cuando exista, esta es la unica funcion que hay que cambiar. */
export function useGoldenHours(unitId: string) {
  const [remainingMs, setRemainingMs] = useState(() => {
    const start = loadStart(unitId);
    return GOLDEN_HOURS_MS - (Date.now() - start);
  });

  useEffect(() => {
    const start = loadStart(unitId);
    const tick = () => setRemainingMs(GOLDEN_HOURS_MS - (Date.now() - start));
    tick();
    const interval = setInterval(tick, 1000);
    return () => clearInterval(interval);
  }, [unitId]);

  return { label: formatRemaining(remainingMs), expired: remainingMs <= 0 };
}
