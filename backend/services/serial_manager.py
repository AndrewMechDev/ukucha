"""SerialManager: hilo lector + escritura con lock sobre un Transport full-duplex.

Desacoplado del medio fisico: recibe cualquier objeto que implemente el
Protocol Transport (backend/ports/transport.py) -- hoy UdpTransport para
el ESP32-S3 de campo real (WiFi/UDP), MockTransport para desarrollo sin
hardware, o en el futuro SerialTransport si se vuelve a un enlace serial.

Parsea cada linea/datagrama recibido como TelemetryPacket (texto plano
pipe-delimited, ver backend/schemas/uplink.py) y lo entrega via callback.
Escribe ControlCommand de bajada (backend/schemas/downlink.py) de forma
thread-safe, protegidos por un lock para que escrituras concurrentes no se
entrelacen en el mismo enlace.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Callable, Optional

from backend.ports.transport import Transport
from backend.schemas.downlink import ControlCommand
from backend.schemas.uplink import TelemetryPacket, parse_telemetry_line

logger = logging.getLogger(__name__)

PacketCallback = Callable[[TelemetryPacket], None]
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

    def send_command(self, command: ControlCommand) -> None:
        """Serializa y escribe un comando de bajada. Thread-safe: multiples
        llamadas concurrentes no entrelazan bytes en el mismo enlace."""
        line = command.to_wire()
        with self._write_lock:
            if not self._transport.is_open:
                logger.warning("No se pudo enviar comando %r: enlace cerrado", line)
                return
            try:
                self._transport.write(line)
                logger.info("Comando enviado: %s", line.decode("ascii").strip())
            except Exception:
                logger.exception("Fallo al escribir comando %r", line)

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
                        "No se pudo abrir el enlace: %s (reintento en %.1fs)", e, backoff
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
            text = raw.decode("utf-8", errors="ignore").strip()
        except UnicodeDecodeError:
            logger.warning("Linea con bytes invalidos, descartada: %r", raw[:80])
            return
        if not text:
            return
        packet = parse_telemetry_line(text)
        if packet is None:
            return
        try:
            self._on_packet(packet)
        except Exception:
            logger.exception("El callback on_packet fallo procesando TelemetryPacket")

    def _set_link_status(self, up: bool) -> None:
        if up == self._link_up:
            return
        self._link_up = up
        logger.info("Enlace %s", "ARRIBA" if up else "CAIDO")
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

    def _on_packet(packet: TelemetryPacket) -> None:
        logger.info("Paquete recibido: %s", packet.model_dump_json())

    manager = SerialManager(transport=MockTransport(seed=42), on_packet=_on_packet)
    manager.start()

    try:
        time.sleep(2.0)
        manager.send_command(ControlCommand(luces=1, motor_a=80, motor_b=80))
        time.sleep(8.0)
    except KeyboardInterrupt:
        pass
    finally:
        manager.stop()
