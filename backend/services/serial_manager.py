"""SerialManager: hilo lector + escritura con lock sobre un Transport full-duplex.

Desacoplado de pyserial: recibe cualquier objeto que implemente el Protocol
Transport (backend/ports/transport.py). Parsea cada linea como un paquete
de subida (backend/schemas/uplink.py, validado con Pydantic) y lo entrega
via callback. Escribe comandos de bajada (backend/schemas/downlink.py) de
forma thread-safe, protegidos por un lock para que escrituras concurrentes
no se entrelacen byte a byte en el mismo puerto.
"""
from __future__ import annotations

import json
import logging
import threading
import time
from typing import Callable, Optional

from pydantic import ValidationError

from backend.ports.transport import Transport
from backend.schemas.downlink import DownlinkCommand
from backend.schemas.uplink import UplinkPacket, uplink_adapter

logger = logging.getLogger(__name__)

PacketCallback = Callable[[UplinkPacket], None]
LinkStatusCallback = Callable[[bool], None]

_RECONNECT_BACKOFF_INITIAL_S = 1.0
_RECONNECT_BACKOFF_MAX_S = 15.0


class SerialManager:
    def __init__(
        self,
        transport: Transport,
        on_packet: PacketCallback,
        on_link_status: Optional[LinkStatusCallback] = None,
    ):
        self._transport = transport
        self._on_packet = on_packet
        self._on_link_status = on_link_status
        self._write_lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._link_up = False

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True, name="SerialManager")
        self._thread.start()
        logger.info("SerialManager iniciado")

    def stop(self) -> None:
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=3.0)
            self._thread = None
        self._transport.close()
        logger.info("SerialManager detenido")

    def send_command(self, command: DownlinkCommand) -> None:
        """Serializa y escribe un comando de bajada. Thread-safe: multiples
        llamadas concurrentes no entrelazan bytes en el mismo puerto."""
        line = command.model_dump_json().encode("utf-8") + b"\n"
        with self._write_lock:
            if not self._transport.is_open:
                logger.warning(
                    "No se pudo enviar comando cmd_id=%s: enlace serial cerrado",
                    command.cmd_id,
                )
                return
            try:
                self._transport.write(line)
                logger.info(
                    "Comando enviado: target=%s cmd_id=%s command=%s",
                    command.target_node, command.cmd_id, command.command,
                )
            except Exception:
                logger.exception("Fallo al escribir comando cmd_id=%s", command.cmd_id)

    def _run(self) -> None:
        backoff = _RECONNECT_BACKOFF_INITIAL_S
        while self._running:
            if not self._transport.is_open:
                self._set_link_status(False)
                try:
                    self._transport.open()
                    backoff = _RECONNECT_BACKOFF_INITIAL_S
                except Exception as e:
                    logger.error(
                        "No se pudo abrir el enlace serial: %s (reintento en %.1fs)", e, backoff
                    )
                    time.sleep(backoff)
                    backoff = min(backoff * 2, _RECONNECT_BACKOFF_MAX_S)
                    continue

            self._set_link_status(True)
            raw = self._transport.readline()
            if raw is None:
                continue
            self._handle_line(raw)

    def _handle_line(self, raw: bytes) -> None:
        try:
            text = raw.decode("utf-8").strip()
        except UnicodeDecodeError:
            logger.warning("Linea con bytes invalidos, descartada: %r", raw[:80])
            return
        if not text:
            return
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            logger.warning("Linea no es JSON valido, descartada: %s", text[:200])
            return
        try:
            packet = uplink_adapter.validate_python(payload)
        except ValidationError as e:
            logger.warning(
                "Paquete con packet_type=%r no cumple el esquema esperado, descartado: %s",
                payload.get("packet_type"), e,
            )
            return
        try:
            self._on_packet(packet)
        except Exception:
            logger.exception("El callback on_packet fallo procesando %s", type(packet).__name__)

    def _set_link_status(self, up: bool) -> None:
        if up == self._link_up:
            return
        self._link_up = up
        logger.info("Enlace serial %s", "ARRIBA" if up else "CAIDO")
        if self._on_link_status is not None:
            try:
                self._on_link_status(up)
            except Exception:
                logger.exception("on_link_status callback fallo")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    from backend.adapters.mock_transport import MockTransport
    from backend.schemas.uplink import FramePacket

    frame_chunks: dict[int, int] = {}

    def _on_packet(packet: UplinkPacket) -> None:
        if isinstance(packet, FramePacket):
            frame_chunks[packet.frame_id] = frame_chunks.get(packet.frame_id, 0) + 1
            if packet.seq == packet.seq_total - 1:
                logger.info(
                    "Frame %d reensamblado en demo: %d/%d chunks recibidos",
                    packet.frame_id, frame_chunks[packet.frame_id], packet.seq_total,
                )
        else:
            logger.info("Paquete recibido: %s", packet.model_dump_json())

    manager = SerialManager(transport=MockTransport(seed=42), on_packet=_on_packet)
    manager.start()

    try:
        time.sleep(2.0)
        manager.send_command(DownlinkCommand(
            target_node="esp32_s3_no2", cmd_id=1, command="set_leds",
            params={"pattern": "red_solid"},
        ))
        time.sleep(8.0)
    except KeyboardInterrupt:
        pass
    finally:
        manager.stop()
