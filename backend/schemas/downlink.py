"""Comando de bajada (PC -> ESP32-S3 de campo) real, enviado por UDP.

El firmware espera texto plano, no JSON (ver appflores/esp32s3_firmware.ino,
TaskTelemetry: `sscanf(msgComando.c_str(), "C:%d,%d,%d", &lucesVal,
&motorAVal, &motorBVal)`):

    C:<luces>,<motorA>,<motorB>\\n

No hay `target_node` (un solo nodo de campo) ni `cmd_id` en el wire format
-- el `cmd_id` que asigna CommandService es solo para trazabilidad/logs de
este backend, el firmware lo ignora. Tampoco hay confirmacion (`cmd_ack`):
el firmware no responde nada tras aplicar el comando.
"""
from __future__ import annotations

from pydantic import BaseModel


class ControlCommand(BaseModel):
    luces: int
    motor_a: int
    motor_b: int

    def to_wire(self) -> bytes:
        return f"C:{self.luces},{self.motor_a},{self.motor_b}\n".encode("ascii")
