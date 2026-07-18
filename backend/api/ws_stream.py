"""WebSocket de salida: registra/limpia paneles conectados a /ws/stream.

El broadcast real (envio de EnrichedFrameOutput) ocurre en el loop de
app.py, que consume la cola async alimentada por DetectionWorker y escribe
a cada cliente en app.state.stream_clients. Este router solo gestiona el
ciclo de vida de la conexion.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/stream")
async def ws_stream(websocket: WebSocket) -> None:
    await websocket.accept()
    clients: set = websocket.app.state.stream_clients
    clients.add(websocket)
    logger.info("Panel conectado a /ws/stream (%d total)", len(clients))
    try:
        while True:
            # No se espera contenido del panel en este canal; solo se usa
            # para detectar la desconexion (receive bloquea hasta cerrar).
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        clients.discard(websocket)
        logger.info("Panel desconectado de /ws/stream (%d total)", len(clients))
