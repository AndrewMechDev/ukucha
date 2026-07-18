# Skill: UKUCHA Backend — Servidor FastAPI de Telemetria

## Objetivo

Servidor FastAPI que recibe telemetria de gases del ESP32-CAM, eventos de
deteccion de vision (caidas, victimas), y frames JPEG; los almacena en memoria
y los retransmite en tiempo real a dashboards conectados por WebSocket.

Este documento permite regenerar `server.py` identicamente desde cero.

## Dependencias

```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from starlette.websockets import WebSocketState
from datetime import datetime
import cv2
import numpy as np
from collections import deque
```

No hay modelos Pydantic: los endpoints POST reciben `dict` genericos
(`data: dict`) en vez de esquemas tipados. Esto es intencional — el ESP32 y
los detectores de vision envian JSON con forma variable segun el evento.

## App y Middleware

```python
app = FastAPI(title="UKUCHA Backend", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

- Sin `description` explicita en el constructor de `FastAPI`.
- CORS totalmente abierto (`*` en origins/methods/headers) — permite que el
  frontend React/Next.js en otro puerto se conecte sin friccion durante el
  hackathon. No hay `allow_credentials`.

## Almacenamiento en Memoria

```python
telemetria = deque(maxlen=100)
alertas = deque(maxlen=50)
detecciones = deque(maxlen=100)
clientes_ws: list[WebSocket] = []
```

| Store | Tipo | Tamaño max | Contenido |
|---|---|---|---|
| `telemetria` | `deque` | 100 | ultimos payloads de gases/sensores con `ts` y `riesgo` agregados |
| `alertas` | `deque` | 50 | eventos de umbral excedido (`tipo`, `valor`, `limite`, `ts`) |
| `detecciones` | `deque` | 100 | eventos de vision (`tipo`, `ts`, ...) |
| `clientes_ws` | `list[WebSocket]` | sin limite | conexiones WebSocket activas de dashboards |

No hay persistencia en disco ni base de datos: todo vive en memoria del
proceso y se pierde al reiniciar. Comentario explicito en el codigo:
`# Almacenamiento en memoria (suficiente para el hackathon)`.

## Constante LIMITES (D.S. 024-2016-EM, mineria peruana)

```python
LIMITES = {
    "CO":  {"max_ppm": 25},
    "H2S": {"max_ppm": 10},
    "O2":  {"min_pct": 19.5},
    "CH4": {"max_ppm": 5000},
    "NO2": {"max_ppm": 3},
    "CO2": {"max_ppm": 5000},
}
```

**Gap conocido**: el dict `LIMITES` define 6 gases (CO, H2S, O2, CH4, NO2,
CO2), pero la evaluacion de riesgo en `post_telemetria` solo verifica **CO y
H2S**. O2 (min_pct), CH4, NO2 y CO2 estan definidos pero nunca se comparan
contra `data` — no generan alertas ni afectan `riesgo` aunque el ESP32
reporte esos valores. Si se regenera el servidor manteniendo el
comportamiento original, este gap debe preservarse (no agregar chequeos para
los 4 gases restantes salvo que se pida explicitamente extender la logica).

## Endpoints

### `GET /`

```python
@app.get("/")
async def root():
    return {"status": "UKUCHA activo", "timestamp": datetime.now().isoformat()}
```

Health check simple. Sin autenticacion.

### `GET /api/telemetria`

```python
@app.get("/api/telemetria")
async def get_telemetria():
    return list(telemetria)
```

Devuelve el historial completo del deque `telemetria` (hasta 100 items) como
lista JSON, orden de insercion (mas viejo primero).

### `GET /api/alertas`

```python
@app.get("/api/alertas")
async def get_alertas():
    return list(alertas)
```

Devuelve el historial completo del deque `alertas` (hasta 50 items).

### `GET /api/limites`

```python
@app.get("/api/limites")
async def get_limites():
    return LIMITES
```

Expone el dict `LIMITES` tal cual, para que el frontend conozca los umbrales
sin hardcodearlos.

### `POST /api/telemetria`

```python
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
```

Logica exacta:

1. Recibe `data: dict` sin validacion de esquema (acepta cualquier JSON).
2. Agrega `data["ts"]` con `datetime.now().isoformat()`.
3. `riesgo` arranca en `"NORMAL"`.
4. Chequea `data.get("co_ppm", 0) > 25` → si excede, `riesgo = "PELIGRO"` y
   agrega a `alertas` un dict `{"tipo": "CO", "valor": <co_ppm>, "limite": 25, "ts": <ts>}`.
   El `limite` esta **hardcodeado a 25**, no referenciado como
   `LIMITES["CO"]["max_ppm"]`.
5. Chequea `data.get("h2s_ppm", 0) > 10` de la misma forma, `limite`
   hardcodeado a 10.
6. Solo CO y H2S se evalúan (ver gap arriba). Ambos chequeos son
   independientes (no `elif`) — si ambos exceden, se agregan dos alertas y
   `riesgo` queda `"PELIGRO"` (no hay nivel mas grave).
7. `data["riesgo"] = riesgo` se agrega al payload antes de guardarlo.
8. `telemetria.append(data)`.
9. Broadcast a todos los `clientes_ws`: itera sobre `clientes_ws.copy()`
   (copia para poder mutar la lista original durante la iteracion). Si el
   estado del socket no es `WebSocketState.CONNECTED`, lo remueve y
   continua. Si `send_json(data)` falla con
   `WebSocketDisconnect`, `RuntimeError` o `ConnectionResetError`, imprime
   `f"[WS] No se pudo enviar a un cliente, se remueve: {e}"` y remueve el
   socket de `clientes_ws`.
10. Retorna `{"ok": True, "riesgo": riesgo}`.

### `GET /api/detecciones`

```python
@app.get("/api/detecciones")
async def get_detecciones():
    return list(detecciones)
```

Devuelve el historial completo del deque `detecciones` (hasta 100 items).

### `POST /api/deteccion`

```python
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
```

Logica exacta:

1. Recibe `data: dict` sin validacion (mismo patron que `post_telemetria`).
2. Agrega `data["ts"]`.
3. `detecciones.append(data)` — **sin evaluacion de riesgo** (a diferencia de
   `post_telemetria`, aqui no hay logica de umbrales).
4. Broadcast identico al de `post_telemetria`, pero el payload enviado por
   WebSocket es `{"canal": "deteccion", **data}` — agrega el campo `"canal":
   "deteccion"` para que el frontend distinga este tipo de mensaje de la
   telemetria de gases (que no lleva `"canal"`).
5. Retorna `{"ok": True}` (sin campo `riesgo`).

### `POST /api/frame`

```python
@app.post("/api/frame")
async def post_frame(file: UploadFile = File(...)):
    """Recibe un frame JPEG del ESP32-CAM."""
    contents = await file.read()
    img = cv2.imdecode(np.frombuffer(contents, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        return {"error": "No se pudo decodificar"}
    h, w = img.shape[:2]
    return {"ok": True, "res": f"{w}x{h}", "bytes": len(contents)}
```

Logica exacta:

1. Recibe multipart/form-data con campo `file: UploadFile = File(...)`.
2. `contents = await file.read()` — lee los bytes crudos.
3. Decodifica con `cv2.imdecode(np.frombuffer(contents, np.uint8), cv2.IMREAD_COLOR)`.
4. Si `img is None` (decodificacion fallida), retorna
   `{"error": "No se pudo decodificar"}` (nota: sin campo `ok`, y no lanza
   excepcion HTTP — sigue devolviendo 200).
5. Si decodifica bien, extrae `h, w = img.shape[:2]`.
6. Retorna `{"ok": True, "res": f"{w}x{h}", "bytes": len(contents)}`. El
   frame decodificado **no se guarda** en ningun store ni se reenvia por
   WebSocket — solo se valida y se reporta su resolucion/tamaño.

### `WebSocket /ws`

```python
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
```

Logica exacta:

1. `await websocket.accept()`.
2. Agrega el socket a `clientes_ws` y loguea
   `f"[WS] Cliente conectado ({len(clientes_ws)} total)"`.
3. Loop infinito `while True` que espera mensajes de texto entrantes con
   `await websocket.receive_text()` y los loguea con
   `f"[WS] Recibido: {msg}"`. El servidor **no responde** a estos mensajes —
   solo los imprime (el canal `/ws` es principalmente de salida, para
   broadcast desde los endpoints POST).
4. Al desconectar (`WebSocketDisconnect`), remueve el socket de
   `clientes_ws` y loguea
   `f"[WS] Cliente desconectado ({len(clientes_ws)} total)"`.

## Funcion de Broadcast (patron repetido, no extraida)

El broadcast a `clientes_ws` **no esta factorizado en una funcion separada**
— el mismo bloque aparece duplicado en `post_telemetria` y `post_deteccion`,
con la unica diferencia del payload enviado (`data` vs
`{"canal": "deteccion", **data}`):

```python
for ws in clientes_ws.copy():
    if ws.client_state != WebSocketState.CONNECTED:
        clientes_ws.remove(ws)
        continue
    try:
        await ws.send_json(<payload>)
    except (WebSocketDisconnect, RuntimeError, ConnectionResetError) as e:
        print(f"[WS] No se pudo enviar a un cliente, se remueve: {e}")
        clientes_ws.remove(ws)
```

Si se regenera el servidor manteniendo el comportamiento identico, esta
duplicacion debe preservarse (no refactorizar a una funcion `broadcast()`
salvo que se pida explicitamente).

## Lanzamiento

`server.py` **no incluye** un bloque `if __name__ == "__main__":` con
`uvicorn.run(...)`. No hay importacion de `uvicorn` en el archivo. El
servidor se lanza externamente, por ejemplo:

```bash
venv\Scripts\python.exe -m uvicorn server:app --host 0.0.0.0 --port 8000
```

(host/puerto no estan fijados en el codigo — se especifican en el comando de
lanzamiento, no hay defaults documentados dentro de `server.py`).

## Interfaz Completa (resumen)

| Metodo | Path | Request | Response |
|---|---|---|---|
| GET | `/` | — | `{"status": str, "timestamp": str}` |
| GET | `/api/telemetria` | — | `list[dict]` (hasta 100) |
| GET | `/api/alertas` | — | `list[dict]` (hasta 50) |
| GET | `/api/limites` | — | `LIMITES` dict |
| POST | `/api/telemetria` | `dict` (JSON) | `{"ok": True, "riesgo": "NORMAL"\|"PELIGRO"}` |
| GET | `/api/detecciones` | — | `list[dict]` (hasta 100) |
| POST | `/api/deteccion` | `dict` (JSON) | `{"ok": True}` |
| POST | `/api/frame` | `multipart/form-data`, campo `file` | `{"ok": True, "res": "WxH", "bytes": int}` o `{"error": str}` |
| WS | `/ws` | texto (solo loguea) | broadcast JSON de telemetria/detecciones |

## Verificacion

1. `venv\Scripts\python.exe -m uvicorn server:app --reload` → arranca sin
   errores.
2. `GET /` → `{"status": "UKUCHA activo", "timestamp": "..."}`.
3. `POST /api/telemetria` con `{"co_ppm": 30}` → `riesgo` = `"PELIGRO"`,
   aparece en `GET /api/alertas` con `tipo="CO"`, `limite=25`.
4. `POST /api/telemetria` con `{"co_ppm": 10}` → `riesgo` = `"NORMAL"`, sin
   alerta nueva.
5. `POST /api/telemetria` con `{"o2_pct": 15}` (bajo el minimo de 19.5) →
   **no genera alerta ni PELIGRO** (confirma el gap: O2 no se evalua).
6. `POST /api/deteccion` con `{"tipo": "caida_critica"}` → aparece en
   `GET /api/detecciones`, sin campo `riesgo`.
7. Conectar cliente WebSocket a `/ws`, luego `POST /api/telemetria` →
   el cliente recibe el JSON con `ts` y `riesgo` agregados.
8. Conectar cliente WebSocket a `/ws`, luego `POST /api/deteccion` →
   el cliente recibe el JSON con `"canal": "deteccion"` agregado.
9. `POST /api/frame` con un JPEG valido → `{"ok": True, "res": "WxH", "bytes": N}`.
10. `POST /api/frame` con bytes invalidos → `{"error": "No se pudo decodificar"}`.
11. Desconectar el cliente WebSocket → log
    `"[WS] Cliente desconectado (N total)"`, se remueve de `clientes_ws`.

## Referencias

- Archivo original: `server.py` (raiz del proyecto)
- Skills relacionadas: `ukucha/sistema.md` (orquestador que envia eventos a
  `/api/deteccion`)
