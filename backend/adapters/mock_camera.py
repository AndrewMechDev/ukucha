"""MockCameraFeed: genera frames JPEG sinteticos a ~10fps con la misma
interfaz que MjpegClient (start()/stop(), callback (frame_id, jpeg_bytes,
timestamp_ms)) -- para desarrollar/probar el pipeline de deteccion sin
tener el ESP32-CAM real encendido.

No intenta simular el protocolo multipart HTTP (no hace falta): el
consumidor (DetectionWorker.submit_frame) solo necesita bytes JPEG validos.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Callable, Optional

import cv2
import numpy as np

logger = logging.getLogger(__name__)

FrameCallback = Callable[[int, bytes, int], None]

_FRAME_INTERVAL_S = 1.0 / 10  # ~10 fps, similar al QQVGA real del ESP32-CAM
_FRAME_SIZE = (120, 160, 3)  # alto, ancho, canales -- igual a QQVGA (160x120)


class MockCameraFeed:
    def __init__(self, on_frame: FrameCallback, seed: Optional[int] = None):
        self._on_frame = on_frame
        self._rng = np.random.default_rng(seed)
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._frame_id = 0

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True, name="MockCameraFeed")
        self._thread.start()
        logger.info("MockCameraFeed iniciado (simulando ESP32-CAM)")

    def stop(self) -> None:
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        logger.info("MockCameraFeed detenido")

    def _run(self) -> None:
        while self._running:
            t0 = time.monotonic()
            self._emit_frame()
            elapsed = time.monotonic() - t0
            time.sleep(max(0.0, _FRAME_INTERVAL_S - elapsed))

    def _emit_frame(self) -> None:
        color = self._rng.integers(0, 256, size=3, dtype=np.uint8)
        img = np.full(_FRAME_SIZE, color, dtype=np.uint8)
        ok, buf = cv2.imencode(".jpg", img)
        if not ok:
            logger.warning("No se pudo generar JPEG sintetico, se omite el frame")
            return
        self._frame_id += 1
        try:
            self._on_frame(self._frame_id, buf.tobytes(), int(time.time() * 1000))
        except Exception:
            logger.exception("on_frame fallo para frame_id=%d", self._frame_id)
