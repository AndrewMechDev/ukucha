"""CommandService: valida comandos entrantes del panel web, determina el
target_node correcto por tipo de comando (el panel no necesita conocer la
topologia de hardware), asigna un cmd_id incremental, y trackea si llega
confirmacion (CmdAckPacket) dentro de un timeout -- util para depurar
fallos de ESP-NOW en el canal de bajada.
"""
from __future__ import annotations

import itertools
import logging
import threading
import time
from typing import Callable, Dict, Optional, Type

from pydantic import BaseModel, ValidationError

from backend.schemas.downlink import DownlinkCommand

logger = logging.getLogger(__name__)

SendFn = Callable[[DownlinkCommand], None]
LogFn = Callable[[dict], None]

_ACK_TIMEOUT_S = 3.0


class SetMotorsParams(BaseModel):
    m1: int
    m2: int
    m3: int
    m4: int


class SetLedsParams(BaseModel):
    pattern: str


class CameraRestartParams(BaseModel):
    pass


_COMMAND_TARGET_NODE: Dict[str, str] = {
    "set_motors": "esp32_s3_no2",
    "set_leds": "esp32_s3_no2",
    "camera_restart": "esp32_s3_no1",
}

_COMMAND_PARAM_SCHEMA: Dict[str, Type[BaseModel]] = {
    "set_motors": SetMotorsParams,
    "set_leds": SetLedsParams,
    "camera_restart": CameraRestartParams,
}


class CommandService:
    def __init__(
        self,
        send_fn: SendFn,
        ack_timeout_s: float = _ACK_TIMEOUT_S,
        on_log: Optional[LogFn] = None,
    ):
        self._send_fn = send_fn
        self._ack_timeout_s = ack_timeout_s
        self._on_log = on_log
        self._cmd_id_counter = itertools.count(1)
        self._pending: Dict[int, dict] = {}  # cmd_id -> {"timer", "command", "target_node"}
        self._lock = threading.Lock()

    def dispatch(self, command: str, params: dict) -> DownlinkCommand:
        target_node = _COMMAND_TARGET_NODE.get(command)
        schema = _COMMAND_PARAM_SCHEMA.get(command)
        if target_node is None or schema is None:
            raise ValueError(f"Comando desconocido: {command!r}")
        try:
            validated = schema.model_validate(params)
        except ValidationError as e:
            raise ValueError(f"Parametros invalidos para {command!r}: {e}") from e

        cmd_id = next(self._cmd_id_counter)
        cmd = DownlinkCommand(
            target_node=target_node, cmd_id=cmd_id, command=command,
            params=validated.model_dump(),
        )
        self._register_pending(cmd_id, command, target_node)
        self._send_fn(cmd)
        self._log({
            "cmd_id": cmd_id, "command": command, "target_node": target_node,
            "params": cmd.params, "event": "sent", "status": None,
            "ts": time.time(),
        })
        return cmd

    def on_ack(self, cmd_id: int, status: str) -> None:
        with self._lock:
            pending = self._pending.pop(cmd_id, None)
        if pending is not None:
            pending["timer"].cancel()
            logger.info("cmd_id=%d confirmado (status=%s)", cmd_id, status)
            self._log({
                "cmd_id": cmd_id, "command": pending["command"], "target_node": pending["target_node"],
                "params": None, "event": "ack", "status": status, "ts": time.time(),
            })
        else:
            logger.warning(
                "cmd_id=%d recibio ack pero ya no estaba pendiente (timeout previo o duplicado)",
                cmd_id,
            )

    def _register_pending(self, cmd_id: int, command: str, target_node: str) -> None:
        timer = threading.Timer(self._ack_timeout_s, self._on_timeout, args=(cmd_id,))
        timer.daemon = True
        with self._lock:
            self._pending[cmd_id] = {"timer": timer, "command": command, "target_node": target_node}
        timer.start()

    def _on_timeout(self, cmd_id: int) -> None:
        with self._lock:
            pending = self._pending.pop(cmd_id, None)
        if pending is not None:
            logger.warning(
                "cmd_id=%d (%s) SIN CONFIRMACION tras %.1fs -- posible falla ESP-NOW",
                cmd_id, pending["command"], self._ack_timeout_s,
            )
            self._log({
                "cmd_id": cmd_id, "command": pending["command"], "target_node": pending["target_node"],
                "params": None, "event": "timeout", "status": None, "ts": time.time(),
            })

    def _log(self, record: dict) -> None:
        if self._on_log is not None:
            try:
                self._on_log(record)
            except Exception:
                logger.exception("on_log callback fallo para cmd_id=%s", record.get("cmd_id"))
