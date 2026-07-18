"""Adapter de Transport que simula el ESP32-S3 de campo real sin hardware.

Genera lineas de telemetria en el formato pipe-delimited real (ver
backend/schemas/uplink.py y appflores/esp32s3_firmware.ino) a ~10Hz, y
loguea los comandos de bajada recibidos -- **sin simular ack**, porque el
firmware real tampoco lo emite (fidelidad intencional: si el mock
respondiera con un ack inexistente, un desarrollo hecho contra el mock se
rompería al pasar a hardware real).

El video ya no viaja por este Transport (el ESP32-CAM real sirve su propio
stream HTTP MJPEG en un canal separado, ver backend/services/mjpeg_client.py
y backend/adapters/mock_camera.py para su equivalente simulado).
"""
from __future__ import annotations

import logging
import queue
import random
import threading
import time
from typing import Optional

logger = logging.getLogger(__name__)

_TELEMETRY_INTERVAL_S = 0.1  # ~10Hz, igual que el firmware real


class MockTransport:
    """Implementa el Protocol Transport generando trafico sintetico en un hilo aparte."""

    def __init__(self, seed: Optional[int] = None):
        self._rng = random.Random(seed)
        self._queue: "queue.Queue[bytes]" = queue.Queue()
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def open(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._feed_loop, daemon=True, name="MockTransportFeed")
        self._thread.start()
        logger.info("MockTransport iniciado (simulando ESP32-S3 de campo por UDP)")

    def close(self) -> None:
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        logger.info("MockTransport detenido")

    def readline(self) -> Optional[bytes]:
        try:
            return self._queue.get(timeout=0.2)
        except queue.Empty:
            return None

    def write(self, data: bytes) -> int:
        """El firmware real no confirma comandos -- el mock tampoco, a
        proposito (ver docstring del modulo)."""
        try:
            text = data.decode("ascii").strip()
        except UnicodeDecodeError:
            text = repr(data)
        logger.info("MockTransport recibio comando: %s", text)
        return len(data)

    @property
    def is_open(self) -> bool:
        return self._running

    # -- generacion de trafico sintetico --------------------------------

    def _emit_telemetry(self) -> None:
        vol_l = round(self._rng.uniform(0, 15), 1)
        vol_r = round(self._rng.uniform(0, 15), 1)
        lat = -16.4090 + self._rng.uniform(-0.001, 0.001)
        lon = -71.5375 + self._rng.uniform(-0.001, 0.001)
        temp = round(self._rng.uniform(18, 28), 2)
        press = round(self._rng.uniform(1008, 1015), 2)
        hum = round(self._rng.uniform(30, 60), 2)
        # Mismo formato que el firmware real: M:mq7,mq136 (gas, ADC crudo),
        # P:pir (HC-SR501, 0/1) -- se simulan en 0 por simplicidad, el mock
        # no necesita variar estos valores para probar el resto del pipeline.
        line = f"A:{vol_l},{vol_r}|M:0.0,0.0|P:0|G:{lat:.6f},{lon:.6f}|C:{temp},{press},{hum}\n"
        self._queue.put(line.encode("utf-8"))

    def _feed_loop(self) -> None:
        next_telemetry = time.monotonic()
        while self._running:
            now = time.monotonic()
            if now >= next_telemetry:
                self._emit_telemetry()
                next_telemetry = now + _TELEMETRY_INTERVAL_S
            time.sleep(0.01)
