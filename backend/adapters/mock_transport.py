"""Adapter de Transport que simula el hardware (ESP32-S3 No3) sin puerto fisico.

Genera los 3 tipos de paquete de subida (frame fragmentado en chunks JPEG
reales, audio_sensors, env_and_actuation) con timing aproximado a un
sistema real, y responde a comandos de bajada con un cmd_ack simulado tras
un pequeño delay -- como haria el firmware una vez lo implemente. Permite
desarrollar y probar todo el pipeline (reensamblado, deteccion, WS,
comandos) sin esperar al hardware.
"""
from __future__ import annotations

import base64
import json
import logging
import queue
import random
import threading
import time
from typing import Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)

_CHUNK_SIZE = 512
_FRAME_INTERVAL_S = 1.0 / 10  # ~10 fps simulados
_AUDIO_INTERVAL_S = 0.5
_ENV_INTERVAL_S = 1.0
_ACK_DELAY_S = 0.3


class MockTransport:
    """Implementa el Protocol Transport generando trafico sintetico en un hilo aparte."""

    def __init__(self, seed: Optional[int] = None):
        self._rng = random.Random(seed)
        self._queue: "queue.Queue[bytes]" = queue.Queue()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._frame_id = 0

    def open(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._feed_loop, daemon=True, name="MockTransportFeed")
        self._thread.start()
        logger.info("MockTransport iniciado (simulando ESP32-S3 No3)")

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
        """Simula la recepcion de un comando de bajada por No3: responde con
        un cmd_ack tras un delay corto, como haria el firmware real."""
        try:
            cmd = json.loads(data.decode("utf-8").strip())
        except (json.JSONDecodeError, UnicodeDecodeError):
            logger.warning("MockTransport recibio bytes no-JSON en write(): %r", data)
            return len(data)

        logger.info("MockTransport recibio comando: %s", cmd)
        cmd_id = cmd.get("cmd_id")
        target_node = cmd.get("target_node", "esp32_s3_no2")
        if cmd_id is not None:
            threading.Timer(_ACK_DELAY_S, self._emit_ack, args=(target_node, cmd_id)).start()
        return len(data)

    @property
    def is_open(self) -> bool:
        return self._running

    # -- generacion de trafico sintetico --------------------------------

    def _emit_ack(self, node_id: str, cmd_id: int) -> None:
        self._put({
            "node_id": node_id,
            "timestamp_ms": int(time.time() * 1000),
            "packet_type": "cmd_ack",
            "cmd_id": cmd_id,
            "status": "ok",
        })

    def _put(self, packet: dict) -> None:
        line = (json.dumps(packet) + "\n").encode("utf-8")
        self._queue.put(line)

    def _make_fake_jpeg(self) -> bytes:
        img = np.full((120, 160, 3), self._rng.randint(0, 255), dtype=np.uint8)
        ok, buf = cv2.imencode(".jpg", img)
        if not ok:
            raise RuntimeError("No se pudo generar JPEG sintetico")
        return buf.tobytes()

    def _emit_frame(self) -> None:
        self._frame_id += 1
        jpeg_bytes = self._make_fake_jpeg()
        chunks = [jpeg_bytes[i:i + _CHUNK_SIZE] for i in range(0, len(jpeg_bytes), _CHUNK_SIZE)]
        seq_total = len(chunks)
        for seq, chunk in enumerate(chunks):
            self._put({
                "node_id": "esp32_s3_no1",
                "timestamp_ms": int(time.time() * 1000),
                "packet_type": "frame",
                "frame_id": self._frame_id,
                "seq": seq,
                "seq_total": seq_total,
                "payload_b64": base64.b64encode(chunk).decode("ascii"),
            })

    def _emit_audio(self) -> None:
        self._put({
            "node_id": "esp32_s3_no1",
            "timestamp_ms": int(time.time() * 1000),
            "packet_type": "audio_sensors",
            "data": {
                "mic1_db": round(self._rng.uniform(35, 70), 1),
                "mic2_db": round(self._rng.uniform(35, 70), 1),
            },
        })

    def _emit_env(self) -> None:
        self._put({
            "node_id": "esp32_s3_no2",
            "timestamp_ms": int(time.time() * 1000),
            "packet_type": "env_and_actuation",
            "data": {
                "gps": {
                    "lat": -16.4090 + self._rng.uniform(-0.001, 0.001),
                    "lon": -71.5375 + self._rng.uniform(-0.001, 0.001),
                    "fix": True,
                    "sats": self._rng.randint(4, 12),
                },
                "tof_distance_mm": self._rng.randint(50, 2000),
                "dust_pms5003": {
                    "pm1_0": self._rng.randint(5, 30),
                    "pm2_5": self._rng.randint(10, 60),
                    "pm10": self._rng.randint(15, 90),
                },
                "gas_mq7_co": {
                    "raw_adc": self._rng.randint(300, 700),
                    "ppm_est": round(self._rng.uniform(5, 30), 1),
                },
                "gas_mq136_h2s": {
                    "raw_adc": self._rng.randint(300, 700),
                    "ppm_est": round(self._rng.uniform(1, 12), 1),
                },
                "led_state": "green_blink",
                "motors": {"m1": 0, "m2": 0, "m3": 0, "m4": 0},
                "battery_v": round(self._rng.uniform(10.5, 12.6), 1),
                "gyro": None,
            },
        })

    def _feed_loop(self) -> None:
        next_frame = next_audio = next_env = time.monotonic()
        while self._running:
            now = time.monotonic()
            if now >= next_frame:
                self._emit_frame()
                next_frame = now + _FRAME_INTERVAL_S
            if now >= next_audio:
                self._emit_audio()
                next_audio = now + _AUDIO_INTERVAL_S
            if now >= next_env:
                self._emit_env()
                next_env = now + _ENV_INTERVAL_S
            time.sleep(0.01)
