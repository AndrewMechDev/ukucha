import { useEffect, useRef, useState } from "react";
import type { EnrichedFrameOutput } from "../types/telemetry";

export type StreamStatus = "connecting" | "online" | "offline";

const RECONNECT_INITIAL_MS = 1000;
const RECONNECT_MAX_MS = 10000;

function streamUrl(): string {
  const explicit = import.meta.env.VITE_WS_URL as string | undefined;
  if (explicit) return `${explicit}/ws/stream`;
  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}/ws/stream`;
}

/** Se conecta a /ws/stream (via proxy de Vite en dev) y expone el ultimo
 * EnrichedFrameOutput recibido. Reconecta solo con backoff exponencial si
 * el backend se cae o el link WiFi se corta -- mismo criterio que el
 * propio backend usa para sus reconexiones (UdpTransport/MjpegClient). */
export function useUnitStream() {
  const [data, setData] = useState<EnrichedFrameOutput | null>(null);
  const [status, setStatus] = useState<StreamStatus>("connecting");
  const backoffRef = useRef(RECONNECT_INITIAL_MS);

  useEffect(() => {
    let socket: WebSocket | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | undefined;
    let cancelled = false;

    const connect = () => {
      if (cancelled) return;
      setStatus((prev) => (prev === "online" ? prev : "connecting"));
      socket = new WebSocket(streamUrl());

      socket.onopen = () => {
        backoffRef.current = RECONNECT_INITIAL_MS;
        setStatus("online");
      };

      socket.onmessage = (event) => {
        try {
          setData(JSON.parse(event.data) as EnrichedFrameOutput);
        } catch {
          // linea invalida del backend, se ignora este frame puntual
        }
      };

      socket.onclose = () => {
        if (cancelled) return;
        setStatus("offline");
        reconnectTimer = setTimeout(connect, backoffRef.current);
        backoffRef.current = Math.min(backoffRef.current * 2, RECONNECT_MAX_MS);
      };

      socket.onerror = () => {
        socket?.close();
      };
    };

    connect();

    return () => {
      cancelled = true;
      clearTimeout(reconnectTimer);
      socket?.close();
    };
  }, []);

  return { data, status };
}
