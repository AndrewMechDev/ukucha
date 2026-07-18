"""Transport real sobre UDP/WiFi para el ESP32-S3 de campo.

Reemplaza a SerialTransport como adapter por defecto: el hardware real no
usa un enlace serial full-duplex con un "dongle" concentrador -- se conecta
directo a la red WiFi local y envia telemetria por UDP (puerto 5002 por
defecto) a ~10Hz, escuchando comandos de control en otro puerto UDP (4210
por defecto). Ver appflores/esp32s3_firmware.ino y appflores/server.js
(mismo esquema de puertos, replicado aca del lado Python).

La IP del nodo se aprende dinamicamente del primer datagrama de telemetria
recibido (mismo criterio que appflores/server.js: `esp32S3Ip =
rinfo.address`), porque el ESP32-S3 obtiene IP por DHCP y puede cambiar
entre arranques. Mientras no se haya recibido ningun paquete, write() no
puede enviar comandos (no hay destino conocido) y lo loguea sin fallar.
"""
from __future__ import annotations

import logging
import socket
from typing import Optional

logger = logging.getLogger(__name__)

_RECV_BUFFER_SIZE = 2048


class UdpTransport:
    def __init__(
        self,
        listen_port: int = 5002,
        control_port: int = 4210,
        timeout: float = 1.0,
        static_node_ip: Optional[str] = None,
    ):
        self._listen_port = listen_port
        self._control_port = control_port
        self._timeout = timeout
        self._node_ip = static_node_ip
        self._sock: Optional[socket.socket] = None

    def open(self) -> None:
        if self.is_open:
            return
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("0.0.0.0", self._listen_port))
        sock.settimeout(self._timeout)
        self._sock = sock
        logger.info("Socket UDP abierto: escuchando telemetria en :%d", self._listen_port)

    def close(self) -> None:
        if self._sock is not None:
            try:
                self._sock.close()
            except Exception:
                logger.exception("Error cerrando socket UDP")
            finally:
                self._sock = None
                logger.info("Socket UDP cerrado")

    def readline(self) -> Optional[bytes]:
        """Cada datagrama UDP ya es un mensaje completo (a diferencia de un
        stream serial), asi que no hace falta buscar '\\n': se devuelve el
        payload crudo del datagrama, o None si expira el timeout."""
        if self._sock is None:
            return None
        try:
            data, addr = self._sock.recvfrom(_RECV_BUFFER_SIZE)
        except socket.timeout:
            return None
        except OSError as e:
            logger.error("Error leyendo socket UDP: %s", e)
            self.close()
            return None
        # DHCP puede reasignar la IP del ESP32-S3 entre arranques; se
        # actualiza con cada paquete para que los comandos siempre vayan
        # al nodo que esta transmitiendo telemetria en este momento.
        if self._node_ip != addr[0]:
            logger.info("IP del ESP32-S3 de campo detectada/actualizada: %s", addr[0])
            self._node_ip = addr[0]
        return data if data else None

    def write(self, data: bytes) -> int:
        if self._sock is None:
            raise ConnectionError("Socket UDP no esta abierto")
        if self._node_ip is None:
            logger.warning(
                "No se conoce todavia la IP del ESP32-S3 (sin telemetria recibida); "
                "comando descartado: %r",
                data,
            )
            return 0
        try:
            return self._sock.sendto(data, (self._node_ip, self._control_port))
        except OSError as e:
            logger.error(
                "Error enviando comando UDP a %s:%d: %s", self._node_ip, self._control_port, e
            )
            raise

    @property
    def is_open(self) -> bool:
        return self._sock is not None
