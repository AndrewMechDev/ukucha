"""DetectionWorker: corre DetectionService.process_jpeg en un hilo dedicado,
separado del hilo lector serial, para que la inferencia (decenas de ms en
estado estable, con picos de varios segundos en el primer frame por JIT de
CUDA -- ver Fase 3) nunca bloquee la lectura de paquetes entrantes.

Cola acotada: si la deteccion no da abasto, se descartan frames nuevos en
vez de acumular latencia creciente -- mismo criterio que WebcamStream
(siempre trabajar con el dato mas reciente posible).
"""
from __future__ import annotations

import logging
import queue
import threading
from typing import Callable, Optional, Tuple

from backend.services.detection_service import DetectionService

logger = logging.getLogger(__name__)

ResultCallback = Callable[[dict], None]

_DEFAULT_QUEUE_MAXSIZE = 2
_STATS_LOG_EVERY = 50  # frames recibidos entre cada resumen de saturacion


class DetectionWorker:
    def __init__(
        self,
        detection_service: DetectionService,
        on_result: ResultCallback,
        queue_maxsize: int = _DEFAULT_QUEUE_MAXSIZE,
    ):
        self._service = detection_service
        self._on_result = on_result
        self._queue: "queue.Queue[Tuple[int, bytes, int]]" = queue.Queue(maxsize=queue_maxsize)
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._submitted = 0
        self._dropped = 0

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True, name="DetectionWorker")
        self._thread.start()
        logger.info("DetectionWorker iniciado")

    def stop(self) -> None:
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=3.0)
            self._thread = None
        logger.info("DetectionWorker detenido")

    def submit_frame(self, frame_id: int, jpeg_bytes: bytes, timestamp_ms: int) -> None:
        """Thread-safe: pensado para usarse como on_frame_complete de
        FrameReassembler (se llama desde el hilo lector serial). Descarta el
        frame si la cola esta llena -- prioriza no acumular lag sobre no
        perder frames."""
        self._submitted += 1
        try:
            self._queue.put_nowait((frame_id, jpeg_bytes, timestamp_ms))
        except queue.Full:
            self._dropped += 1
            logger.warning(
                "DetectionWorker saturado, se descarta frame_id=%d (deteccion no da abasto)",
                frame_id,
            )
        if self._submitted % _STATS_LOG_EVERY == 0:
            pct = (self._dropped / self._submitted) * 100.0
            logger.info(
                "DetectionWorker: %d frames recibidos, %d descartados (%.1f%%)",
                self._submitted, self._dropped, pct,
            )

    def _run(self) -> None:
        while self._running:
            try:
                frame_id, jpeg_bytes, timestamp_ms = self._queue.get(timeout=0.2)
            except queue.Empty:
                continue
            try:
                result = self._service.process_jpeg(frame_id, jpeg_bytes, timestamp_ms)
            except Exception:
                logger.exception("DetectionService fallo procesando frame_id=%d", frame_id)
                continue
            if result is None:
                continue
            try:
                self._on_result(result)
            except Exception:
                logger.exception("on_result callback fallo para frame_id=%d", frame_id)
