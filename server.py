"""
UKUCHA Backend — Servidor FastAPI para telemetría del ESP32-CAM.
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from starlette.websockets import WebSocketState
from datetime import datetime
import cv2
import numpy as np
from collections import deque

app = FastAPI(title="UKUCHA Backend", version="0.1.0")

# CORS: permite que el frontend (React/Next.js en otro puerto) se conecte
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Almacenamiento en memoria (suficiente para el hackathon)
telemetria = deque(maxlen=100)
alertas = deque(maxlen=50)
detecciones = deque(maxlen=100)
clientes_ws: list[WebSocket] = []

# Límites D.S. 024-2016-EM (minería peruana)
LIMITES = {
    "CO":  {"max_ppm": 25},
    "H2S": {"max_ppm": 10},
    "O2":  {"min_pct": 19.5},
    "CH4": {"max_ppm": 5000},
    "NO2": {"max_ppm": 3},
    "CO2": {"max_ppm": 5000},
}


@app.get("/")
async def root():
    return {"status": "UKUCHA activo", "timestamp": datetime.now().isoformat()}


@app.get("/api/telemetria")
async def get_telemetria():
    return list(telemetria)


@app.get("/api/alertas")
async def get_alertas():
    return list(alertas)


@app.get("/api/limites")
async def get_limites():
    return LIMITES


@app.post("/api/telemetria")
async def post_telemetria(data: dict):
    """El ESP32 envía datos aquí. Ejemplo:
    {"co_ppm": 12.5, "h2s_ppm": 3.2, "temp_c": 28.4, "humedad_pct": 65}
    """
    data["ts"] = datetime.now().isoformat()
    riesgo = "NORMAL"

    if data.get("co_ppm", 0) > LIMITES["CO"]["max_ppm"]:
        riesgo = "PELIGRO"
        alertas.append({"tipo": "CO", "valor": data["co_ppm"], "limite": 25, "ts": data["ts"]})
    if data.get("h2s_ppm", 0) > LIMITES["H2S"]["max_ppm"]:
        riesgo = "PELIGRO"
        alertas.append({"tipo": "H2S", "valor": data["h2s_ppm"], "limite": 10, "ts": data["ts"]})

    data["riesgo"] = riesgo
    telemetria.append(data)

    # Notificar a dashboards conectados por WebSocket
    for ws in clientes_ws.copy():
        if ws.client_state != WebSocketState.CONNECTED:
            clientes_ws.remove(ws)
            continue
        try:
            await ws.send_json(data)
        except (WebSocketDisconnect, RuntimeError, ConnectionResetError) as e:
            print(f"[WS] No se pudo enviar a un cliente, se remueve: {e}")
            clientes_ws.remove(ws)

    return {"ok": True, "riesgo": riesgo}


@app.get("/api/detecciones")
async def get_detecciones():
    return list(detecciones)


@app.post("/api/deteccion")
async def post_deteccion(data: dict):
    """Los detectores de vision (ukucha_detector.py) envian eventos aqui.
    Ejemplo:
    {"tipo": "caida_detectada"|"caida_critica"|"victima_confirmada", ...}
    """
    data["ts"] = datetime.now().isoformat()
    detecciones.append(data)

    for ws in clientes_ws.copy():
        if ws.client_state != WebSocketState.CONNECTED:
            clientes_ws.remove(ws)
            continue
        try:
            await ws.send_json({"canal": "deteccion", **data})
        except (WebSocketDisconnect, RuntimeError, ConnectionResetError) as e:
            print(f"[WS] No se pudo enviar a un cliente, se remueve: {e}")
            clientes_ws.remove(ws)

    return {"ok": True}


@app.post("/api/frame")
async def post_frame(file: UploadFile = File(...)):
    """Recibe un frame JPEG del ESP32-CAM."""
    contents = await file.read()
    img = cv2.imdecode(np.frombuffer(contents, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        return {"error": "No se pudo decodificar"}
    h, w = img.shape[:2]
    return {"ok": True, "res": f"{w}x{h}", "bytes": len(contents)}


@app.websocket("/ws")
async def ws_telemetria(websocket: WebSocket):
    """Dashboard se conecta aquí para tiempo real."""
    await websocket.accept()
    clientes_ws.append(websocket)
    print(f"[WS] Cliente conectado ({len(clientes_ws)} total)")
    try:
        while True:
            msg = await websocket.receive_text()
            print(f"[WS] Recibido: {msg}")
    except WebSocketDisconnect:
        clientes_ws.remove(websocket)
        print(f"[WS] Cliente desconectado ({len(clientes_ws)} total)")