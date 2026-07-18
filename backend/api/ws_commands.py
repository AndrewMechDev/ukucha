"""Canal de comandos: el panel web envia set_actuators (luces + 2 motores,
el unico comando que soporta el firmware real) por WebSocket (tiempo real,
/ws/commands) o REST (conveniencia/testing, POST /api/commands). Ambos
delegan en CommandService, que valida parametros, asigna cmd_id, y escribe
el comando por UDP hacia el ESP32-S3 de campo.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field, ValidationError

from backend.api.deps import get_command_service
from backend.services.command_service import CommandService

logger = logging.getLogger(__name__)

router = APIRouter()


class IncomingCommandRequest(BaseModel):
    command: str
    params: dict = Field(default_factory=dict)


@router.websocket("/ws/commands")
async def ws_commands(websocket: WebSocket) -> None:
    await websocket.accept()
    command_service: CommandService = websocket.app.state.command_service
    logger.info("Panel conectado a /ws/commands")
    try:
        while True:
            raw = await websocket.receive_json()
            try:
                req = IncomingCommandRequest.model_validate(raw)
                cmd = command_service.dispatch(req.command, req.params)
            except (ValidationError, ValueError) as e:
                await websocket.send_json({"ok": False, "error": str(e)})
                continue
            await websocket.send_json({"ok": True, "cmd_id": cmd.cmd_id, "command": cmd.command})
    except WebSocketDisconnect:
        logger.info("Panel desconectado de /ws/commands")


@router.post("/api/commands")
async def post_command(
    req: IncomingCommandRequest,
    command_service: CommandService = Depends(get_command_service),
) -> dict:
    try:
        cmd = command_service.dispatch(req.command, req.params)
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    return {"ok": True, "cmd_id": cmd.cmd_id, "command": cmd.command}
