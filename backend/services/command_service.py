"""CommandService: valida comandos entrantes del panel web, asigna un
cmd_id incremental (solo para trazabilidad/logs de este backend -- el
firmware real no lo usa ni lo devuelve) y despacha el ControlCommand real
por UDP.

El hardware real (appflores/esp32s3_firmware.ino) tiene un unico comando
de bajada que combina luces + 2 motores en una sola linea (`C:l,mA,mB`) y
**no confirma nada**: no hay CmdAckPacket, ni endpoint de reinicio de
camara (el ESP32-CAM es solo un servidor de streaming, sin canal de
control). El timeout de esta clase queda solo para diagnostico/logging;
nunca bloquea ni reintenta, y esta preparado para cuando el firmware
agregue un ack real sin requerir cambios en la interfaz publica.
"""
from __future__ import annotations

import itertools
import logging
import threading
from dataclasses import dataclass
from typing import Callable, Dict, Optional, Type

from pydantic import BaseModel, ValidationError

from backend.schemas.downlink import ControlCommand

logger = logging.getLogger(__name__)

SendFn = Callable[[ControlCommand], None]
LogFn = Callable[[dict], None]

_ACK_TIMEOUT_S = 3.0


class SetActuatorsParams(BaseModel):
    luces: int
    motor_a: int
    motor_b: int


_COMMAND_PARAM_SCHEMA: Dict[str, Type[BaseModel]] = {
    "set_actuators": SetActuatorsParams,
}


@dataclass
class DispatchResult:
    """El wire format (ControlCommand) no lleva cmd_id/command -- el
    firmware real no los necesita. DispatchResult los expone para que la
    capa API (ws_commands.py) pueda responder al panel sin conocer el
    formato de bajada."""

    cmd_id: int
    command: str
    control: ControlCommand


class CommandService:
    def __init__(
        self,
        send_fn: SendFn,
        ack_timeout_s: float = _ACK_TIMEOUT_S,
        on_log: Optional[LogFn] = None,
        target_node: str = "esp32s3_campo",
    ):
        self._send_fn = send_fn
        self._ack_timeout_s = ack_timeout_s
        self._on_log = on_log
        self._target_node = target_node
        self._cmd_id_counter = itertools.count(1)
        self._pending: Dict[int, dict] = {}  # cmd_id -> {"timer", "command"}
        self._lock = threading.Lock()

    def dispatch(self, command: str, params: dict) -> DispatchResult:
        schema = _COMMAND_PARAM_SCHEMA.get(command)
        if schema is None:
            raise ValueError(f"Comando desconocido: {command!r}")
        try:
            validated = schema.model_validate(params)
        except ValidationError as e:
            raise ValueError(f"Parametros invalidos para {command!r}: {e}") from e

        cmd_id = next(self._cmd_id_counter)
        cmd = ControlCommand(**validated.model_dump())
        self._register_pending(cmd_id, command)
        self._send_fn(cmd)
        self._log({
            "cmd_id": cmd_id, "command": command, "params": validated.model_dump(),
            "target_node": self._target_node, "event": "sent", "status": None,
        })
        return DispatchResult(cmd_id=cmd_id, command=command, control=cmd)

    def on_ack(self, cmd_id: int, status: str) -> None:
        """El firmware actual nunca llama a esto (no emite ack). Se deja
        cableado para cuando lo implemente sin requerir cambios aca."""
        with self._lock:
            pending = self._pending.pop(cmd_id, None)
        if pending is not None:
            pending["timer"].cancel()
            logger.info("cmd_id=%d confirmado (status=%s)", cmd_id, status)
            self._log({
                "cmd_id": cmd_id, "command": pending["command"], "params": None,
                "target_node": self._target_node, "event": "ack", "status": status,
            })
        else:
            logger.warning(
                "cmd_id=%d recibio ack pero ya no estaba pendiente (timeout previo o duplicado)",
                cmd_id,
            )

    def _register_pending(self, cmd_id: int, command: str) -> None:
        timer = threading.Timer(self._ack_timeout_s, self._on_timeout, args=(cmd_id,))
        timer.daemon = True
        with self._lock:
            self._pending[cmd_id] = {"timer": timer, "command": command}
        timer.start()

    def _on_timeout(self, cmd_id: int) -> None:
        with self._lock:
            pending = self._pending.pop(cmd_id, None)
        if pending is not None:
            logger.info(
                "cmd_id=%d (%s) sin confirmacion tras %.1fs -- esperado, el "
                "firmware actual no emite ack",
                cmd_id, pending["command"], self._ack_timeout_s,
            )
            self._log({
                "cmd_id": cmd_id, "command": pending["command"], "params": None,
                "target_node": self._target_node, "event": "timeout", "status": None,
            })

    def _log(self, record: dict) -> None:
        if self._on_log is not None:
            try:
                self._on_log(record)
            except Exception:
                logger.exception("on_log callback fallo para cmd_id=%s", record.get("cmd_id"))
