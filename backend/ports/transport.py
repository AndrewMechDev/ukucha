"""Puerto del enlace fisico full-duplex hacia el hardware (ESP32-S3 No3).

Cualquier fuente de datos (serial real, mock, TCP/WiFi a futuro) implementa
este Protocol para que SerialManager no dependa de pyserial ni de ninguna
implementacion concreta — es el mecanismo que permite "reemplazar la fuente
serial despues sin tocar YOLO ni el WebSocket".
"""
from __future__ import annotations

from typing import Optional, Protocol


class Transport(Protocol):
    def open(self) -> None:
        """Abre el enlace. Debe ser idempotente si ya esta abierto."""
        ...

    def close(self) -> None:
        """Cierra el enlace. Debe ser idempotente si ya esta cerrado."""
        ...

    def readline(self) -> Optional[bytes]:
        """Lee una linea terminada en \\n. None si no hay datos dentro del
        timeout o si el enlace no esta abierto (nunca bytes vacios)."""
        ...

    def write(self, data: bytes) -> int:
        """Escribe bytes crudos. Retorna cantidad de bytes escritos."""
        ...

    @property
    def is_open(self) -> bool:
        ...
