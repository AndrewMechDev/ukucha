"""Adapter de Transport sobre pyserial: puerto USB real hacia ESP32-S3 No3.

HISTORICO / SIN USO -- el hardware real quedo confirmado 100% WiFi (ver
UdpTransport y .claude/skills/ukucha/backend-conexion.md): no hay ni va a
haber enlace USB. `app.py` nunca importa esta clase; se conserva solo como
referencia del diseño original con dongle serial. `pyserial` NO esta en
requirements.txt (se saco por no tener uso real), por eso el import queda
perezoso adentro de open() -- este modulo se puede seguir importando sin
romper nada aunque pyserial no este instalado.
"""
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class SerialTransport:
    """Implementa el Protocol Transport usando pyserial.Serial."""

    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 1.0):
        self._port = port
        self._baudrate = baudrate
        self._timeout = timeout
        self._ser: Optional[serial.Serial] = None

    def open(self) -> None:
        if self.is_open:
            return
        import serial  # import perezoso -- ver nota "HISTORICO / SIN USO" arriba

        self._ser = serial.Serial(
            port=self._port,
            baudrate=self._baudrate,
            timeout=self._timeout,
            write_timeout=self._timeout,
        )
        logger.info("Puerto serial abierto: %s @ %d baud", self._port, self._baudrate)

    def close(self) -> None:
        if self._ser is not None:
            try:
                self._ser.close()
            except Exception:
                logger.exception("Error cerrando puerto serial %s", self._port)
            finally:
                self._ser = None
                logger.info("Puerto serial cerrado: %s", self._port)

    def readline(self) -> Optional[bytes]:
        if self._ser is None:
            return None
        import serial  # import perezoso -- ver nota "HISTORICO / SIN USO" arriba

        try:
            line = self._ser.readline()
        except (serial.SerialException, OSError) as e:
            logger.error("Error leyendo puerto serial %s: %s", self._port, e)
            self.close()
            return None
        # pyserial devuelve b"" (no None) cuando expira el timeout sin datos;
        # lo traducimos a None para cumplir el contrato del Protocol Transport.
        return line if line else None

    def write(self, data: bytes) -> int:
        if self._ser is None:
            raise ConnectionError(f"Puerto serial {self._port} no esta abierto")
        import serial  # import perezoso -- ver nota "HISTORICO / SIN USO" arriba

        try:
            return self._ser.write(data)
        except (serial.SerialException, OSError) as e:
            logger.error("Error escribiendo en puerto serial %s: %s", self._port, e)
            self.close()
            raise

    @property
    def is_open(self) -> bool:
        return self._ser is not None and self._ser.is_open
