"""TelemetryStore: guarda el ultimo TelemetryPacket conocido del ESP32-S3 de
campo, marcando 'stale' si no llega un paquete fresco dentro de
stale_after_s segundos (posible falla del enlace WiFi/UDP).

A diferencia del diseño original (audio_sensors y env_and_actuation como
paquetes separados de 2 "nodos" distintos), el hardware real envia un
unico TelemetryPacket combinado por el ESP32-S3 de campo -- por eso hay un
solo timestamp de recepcion, no dos.

Thread-safe: se escribe desde el hilo lector de SerialManager y se lee
desde el loop de broadcast (asyncio, otro hilo del proceso).
"""
from __future__ import annotations

import threading
import time
from typing import Optional

from backend.schemas.uplink import TelemetryPacket

_DEFAULT_STALE_AFTER_S = 5.0


class TelemetryStore:
    def __init__(self, stale_after_s: float = _DEFAULT_STALE_AFTER_S):
        self._stale_after_s = stale_after_s
        self._lock = threading.Lock()
        self._packet: Optional[TelemetryPacket] = None
        self._received_at: Optional[float] = None

    def update(self, packet: TelemetryPacket) -> None:
        with self._lock:
            self._packet = packet
            self._received_at = time.monotonic()

    def get_audio(self) -> dict:
        packet, stale = self._snapshot()
        if packet is None:
            return {"vol_l": None, "vol_r": None, "stale": True}
        return {"vol_l": packet.audio.vol_l, "vol_r": packet.audio.vol_r, "stale": stale}

    def get_env(self) -> dict:
        packet, stale = self._snapshot()
        if packet is None:
            return {"gps": None, "gas": None, "pir_detected": None, "climate": None, "stale": True}
        return {
            "gps": packet.gps,
            "gas": packet.gas,
            "pir_detected": packet.pir_detected,
            "climate": packet.climate,
            "stale": stale,
        }

    def _snapshot(self) -> tuple[Optional[TelemetryPacket], bool]:
        with self._lock:
            packet, received_at = self._packet, self._received_at
        if packet is None:
            return None, True
        stale = (time.monotonic() - received_at) > self._stale_after_s
        return packet, stale
