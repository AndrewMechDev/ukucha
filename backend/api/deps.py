"""Dependencias FastAPI: acceso a los singletons compartidos en app.state
para inyectarlos en endpoints REST (los WS los leen directo de
websocket.app.state, patron equivalente pero sin el mecanismo Depends)."""
from __future__ import annotations

from fastapi import Request

from backend.services.command_service import CommandService


def get_command_service(request: Request) -> CommandService:
    return request.app.state.command_service
