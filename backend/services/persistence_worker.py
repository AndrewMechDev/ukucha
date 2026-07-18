"""PersistenceWorker: escribe al backend de persistencia configurado
(Supabase u otro) en un hilo daemon aparte con una cola acotada, para que
nunca bloquee ni haga mas lento el pipeline en tiempo real.

Mismo patron que ServerNotifier en ukucha_detector.py: si el backend esta
caido, lento, o no configurado, los registros simplemente se descartan
-- nunca se traba ni se propaga una excepcion hacia el resto del backend.
"""
from __future__ import annotations

import logging
import queue
import threading
from typing import Dict, Optional, Tuple

from backend.ports.persistence import PersistenceBackend

logger = logging.getLogger(__name__)

_QUEUE_MAXSIZE = 200


class PersistenceWorker:
    def __init__(self, backend: PersistenceBackend, queue_maxsize: int = _QUEUE_MAXSIZE):
        self._backend = backend
        self._queue: "queue.Queue[Tuple[str, dict]]" = queue.Queue(maxsize=queue_maxsize)
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._warned: Dict[str, bool] = {}

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True, name="PersistenceWorker")
        self._thread.start()
        logger.info("PersistenceWorker iniciado (backend=%s)", type(self._backend).__name__)

    def stop(self) -> None:
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=3.0)
            self._thread = None
        logger.info("PersistenceWorker detenido")

    def save_event(self, event: dict) -> None:
        self._enqueue("event", event)

    def save_telemetry(self, record: dict) -> None:
        self._enqueue("telemetry", record)

    def save_command_log(self, record: dict) -> None:
        self._enqueue("command", record)

    def _enqueue(self, kind: str, record: dict) -> None:
        try:
            self._queue.put_nowait((kind, record))
        except queue.Full:
            pass  # backend lento/caido: se descarta, no se acumula lag

    def _run(self) -> None:
        while self._running:
            try:
                kind, record = self._queue.get(timeout=0.2)
            except queue.Empty:
                continue
            try:
                if kind == "event":
                    self._backend.save_event(record)
                elif kind == "telemetry":
                    self._backend.save_telemetry(record)
                elif kind == "command":
                    self._backend.save_command_log(record)
            except Exception as e:
                if not self._warned.get(kind):
                    logger.warning(
                        "Fallo al persistir %s (se silencian avisos futuros de este tipo): %s",
                        kind, e,
                    )
                    self._warned[kind] = True
