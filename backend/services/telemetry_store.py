"""TelemetryStore: guarda el ultimo estado conocido de audio_sensors y
env_and_actuation, marcando 'stale' si no llegan datos frescos dentro de
stale_after_s segundos (posible falla del enlace ESP-NOW hacia No1/No2).

Thread-safe: se escribe desde el hilo lector de SerialManager y se lee
desde el loop de broadcast (asyncio, otro hilo del proceso).
"""
from __future__ import annotations

import threading
import time
from typing import Optional

from backend.schemas.uplink import AudioSensorsPacket, EnvActuationPacket

_DEFAULT_STALE_AFTER_S = 5.0


class TelemetryStore:
    def __init__(self, stale_after_s: float = _DEFAULT_STALE_AFTER_S):
        self._stale_after_s = stale_after_s
        self._lock = threading.Lock()
        self._audio: Optional[AudioSensorsPacket] = None
        self._audio_received_at: Optional[float] = None
        self._env: Optional[EnvActuationPacket] = None
        self._env_received_at: Optional[float] = None

    def update_audio(self, packet: AudioSensorsPacket) -> None:
        with self._lock:
            self._audio = packet
            self._audio_received_at = time.monotonic()

    def update_env(self, packet: EnvActuationPacket) -> None:
        with self._lock:
            self._env = packet
            self._env_received_at = time.monotonic()

    def get_audio(self) -> dict:
        with self._lock:
            packet, received_at = self._audio, self._audio_received_at
        if packet is None:
            return {"mic1_db": None, "mic2_db": None, "stale": True}
        stale = (time.monotonic() - received_at) > self._stale_after_s
        return {"mic1_db": packet.data.mic1_db, "mic2_db": packet.data.mic2_db, "stale": stale}

    def get_env(self) -> dict:
        with self._lock:
            packet, received_at = self._env, self._env_received_at
        if packet is None:
            return {
                "gps": None, "tof_distance_mm": None, "dust_pms5003": None,
                "gas_mq7_co": None, "gas_mq136_h2s": None, "led_state": None,
                "battery_v": None, "stale": True, "motors": None,
            }
        stale = (time.monotonic() - received_at) > self._stale_after_s
        data = packet.data
        return {
            "gps": data.gps,
            "tof_distance_mm": data.tof_distance_mm,
            "dust_pms5003": data.dust_pms5003,
            "gas_mq7_co": data.gas_mq7_co,
            "gas_mq136_h2s": data.gas_mq136_h2s,
            "led_state": data.led_state,
            "battery_v": data.battery_v,
            "stale": stale,
            "motors": data.motors,
        }
