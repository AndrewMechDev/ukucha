"""FrameReassembler: reconstruye frames JPEG completos a partir de fragmentos
FramePacket (seq/seq_total) que llegan potencialmente fuera de orden o
incompletos por perdida de paquetes en el trayecto ESP-NOW -> USB serial.

Frames que no completan todos sus chunks dentro de timeout_s se descartan
(nunca se entregan a deteccion) y quedan logueados para diagnostico.
"""
from __future__ import annotations

import base64
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from backend.schemas.uplink import FramePacket

logger = logging.getLogger(__name__)

# frame_id, jpeg_bytes, timestamp_ms del primer chunk
FrameCompleteCallback = Callable[[int, bytes, int], None]

_DEFAULT_TIMEOUT_S = 2.0
_DEFAULT_PRUNE_INTERVAL_S = 0.5


@dataclass
class _PendingFrame:
    seq_total: int
    node_id: str
    timestamp_ms: int
    chunks: dict = field(default_factory=dict)  # seq -> bytes
    first_seen: float = field(default_factory=time.monotonic)

    def is_complete(self) -> bool:
        return len(self.chunks) == self.seq_total

    def assemble(self) -> bytes:
        return b"".join(self.chunks[i] for i in range(self.seq_total))


class FrameReassembler:
    """Recibe FramePacket via add_chunk(); entrega frames completos via
    on_frame_complete. Corre un hilo de poda en background para descartar
    frames incompletos sin depender de que sigan llegando chunks nuevos."""

    def __init__(
        self,
        on_frame_complete: FrameCompleteCallback,
        timeout_s: float = _DEFAULT_TIMEOUT_S,
        prune_interval_s: float = _DEFAULT_PRUNE_INTERVAL_S,
    ):
        self._on_frame_complete = on_frame_complete
        self._timeout_s = timeout_s
        self._prune_interval_s = prune_interval_s
        self._pending: dict[int, _PendingFrame] = {}
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._prune_loop, daemon=True, name="FrameReassemblerPrune"
        )
        self._thread.start()
        logger.info("FrameReassembler iniciado (timeout=%.1fs)", self._timeout_s)

    def stop(self) -> None:
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        logger.info("FrameReassembler detenido")

    def add_chunk(self, packet: FramePacket) -> None:
        if packet.seq_total <= 0 or not (0 <= packet.seq < packet.seq_total):
            logger.warning(
                "Chunk con seq/seq_total invalido, descartado: frame_id=%d seq=%d seq_total=%d",
                packet.frame_id, packet.seq, packet.seq_total,
            )
            return
        try:
            chunk = base64.b64decode(packet.payload_b64, validate=True)
        except Exception as e:
            logger.warning(
                "Chunk invalido (frame_id=%d seq=%d): no se pudo decodificar base64: %s",
                packet.frame_id, packet.seq, e,
            )
            return

        complete_frame: Optional[_PendingFrame] = None
        with self._lock:
            pending = self._pending.get(packet.frame_id)
            if pending is None or pending.seq_total != packet.seq_total:
                if pending is not None:
                    logger.warning(
                        "frame_id=%d cambio seq_total (%d -> %d) a mitad de reensamblado, se reinicia",
                        packet.frame_id, pending.seq_total, packet.seq_total,
                    )
                pending = _PendingFrame(
                    seq_total=packet.seq_total,
                    node_id=packet.node_id,
                    timestamp_ms=packet.timestamp_ms,
                )
                self._pending[packet.frame_id] = pending

            if packet.seq in pending.chunks:
                logger.debug(
                    "Chunk duplicado ignorado: frame_id=%d seq=%d", packet.frame_id, packet.seq
                )
            else:
                pending.chunks[packet.seq] = chunk

            if pending.is_complete():
                complete_frame = pending
                del self._pending[packet.frame_id]

        if complete_frame is not None:
            self._deliver(packet.frame_id, complete_frame)

    def _deliver(self, frame_id: int, pending: _PendingFrame) -> None:
        try:
            jpeg_bytes = pending.assemble()
        except Exception:
            logger.exception("Fallo al ensamblar frame_id=%d pese a estar completo", frame_id)
            return
        try:
            self._on_frame_complete(frame_id, jpeg_bytes, pending.timestamp_ms)
        except Exception:
            logger.exception("on_frame_complete fallo para frame_id=%d", frame_id)

    def _prune_loop(self) -> None:
        while self._running:
            self._prune_stale()
            time.sleep(self._prune_interval_s)

    def _prune_stale(self) -> None:
        now = time.monotonic()
        with self._lock:
            stale_ids = [
                fid for fid, p in self._pending.items() if now - p.first_seen > self._timeout_s
            ]
            removed = [(fid, self._pending.pop(fid)) for fid in stale_ids]
        for fid, p in removed:
            logger.warning(
                "Frame %d descartado por timeout: %d/%d chunks recibidos (%.1fs)",
                fid, len(p.chunks), p.seq_total, now - p.first_seen,
            )


if __name__ == "__main__":
    import cv2
    import numpy as np

    from backend.adapters.mock_transport import MockTransport
    from backend.schemas.downlink import DownlinkCommand
    from backend.schemas.uplink import FramePacket, UplinkPacket
    from backend.services.serial_manager import SerialManager

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    def _on_frame_complete(frame_id: int, jpeg_bytes: bytes, timestamp_ms: int) -> None:
        img = cv2.imdecode(np.frombuffer(jpeg_bytes, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            logger.error("Frame %d reensamblado pero NO decodifica como JPEG valido", frame_id)
            return
        logger.info(
            "Frame %d OK: %d bytes, decodificado a %dx%d",
            frame_id, len(jpeg_bytes), img.shape[1], img.shape[0],
        )

    reassembler = FrameReassembler(on_frame_complete=_on_frame_complete, timeout_s=1.0)
    reassembler.start()

    def _on_packet(packet: UplinkPacket) -> None:
        if isinstance(packet, FramePacket):
            reassembler.add_chunk(packet)

    manager = SerialManager(transport=MockTransport(seed=7), on_packet=_on_packet)
    manager.start()

    try:
        time.sleep(1.5)

        # Fuerza un frame incompleto a proposito: solo el primer chunk de 3,
        # para verificar que _prune_stale() lo descarta tras el timeout.
        logger.info("--- Inyectando frame incompleto (frame_id=99999) para probar timeout ---")
        incomplete = FramePacket(
            node_id="esp32_s3_no1",
            timestamp_ms=int(time.time() * 1000),
            packet_type="frame",
            frame_id=99999,
            seq=0,
            seq_total=3,
            payload_b64=base64.b64encode(b"chunk-incompleto").decode("ascii"),
        )
        reassembler.add_chunk(incomplete)

        time.sleep(3.0)
    except KeyboardInterrupt:
        pass
    finally:
        manager.stop()
        reassembler.stop()
