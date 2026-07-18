"""app.py — arma el backend UKUCHA completo contra el hardware real: enlace
UDP/WiFi de telemetria+comandos con el ESP32-S3 de campo, stream HTTP MJPEG
del ESP32-CAM, deteccion (caidas + EPP + escombros + fusion), telemetria
con staleness, comandos sin ack (fidelidad al firmware real), y
persistencia no bloqueante (Supabase o NullPersistenceAdapter), expuesto
via FastAPI (WebSocket + REST).

Config por variable de entorno (todas opcionales; sin ninguna, el backend
arranca en modo desarrollo completo: mocks de sensor + camara + sin
persistencia real):
    UKUCHA_USE_MOCK=1           usar MockTransport + MockCameraFeed en vez
                                 del hardware real
    UKUCHA_TELEMETRY_PORT=5002  puerto UDP donde el ESP32-S3 envia telemetria
    UKUCHA_CONTROL_PORT=4210    puerto UDP donde el ESP32-S3 escucha comandos
    UKUCHA_CAM_URL=http://192.168.4.1/  URL del stream MJPEG del ESP32-CAM
                                 (ignorado si UKUCHA_USE_MOCK=1)
    UKUCHA_ENV_EVERY=5          correr RescueDetector 1 de cada N frames
    SUPABASE_URL / SUPABASE_KEY  si faltan, se usa NullPersistenceAdapter
        (loguea lo que se hubiera guardado, no persiste nada, el resto del
        backend funciona identico -- ver env.example para copiar a .env)

NOTA: `app = create_app()` corre a nivel de modulo (carga los 3 modelos
YOLO + MediaPipe + warm-up de CUDA como efecto secundario de importar este
archivo), necesario para que `uvicorn backend.app:app` encuentre el objeto
ASGI. Pensado para un solo proceso/worker (una GPU) -- NO usar
`uvicorn --workers N>1` con este archivo: cada worker duplicaria los 3
modelos en VRAM.
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager

import cv2
import numpy as np
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.adapters.mock_camera import MockCameraFeed
from backend.adapters.mock_transport import MockTransport
from backend.adapters.null_adapter import NullPersistenceAdapter
from backend.adapters.udp_transport import UdpTransport
from backend.api.ws_commands import router as commands_router
from backend.api.ws_stream import router as stream_router
from backend.ports.persistence import PersistenceBackend
from backend.schemas.uplink import TelemetryPacket
from backend.services.command_service import CommandService
from backend.services.detection_service import DetectionService
from backend.services.detection_worker import DetectionWorker
from backend.services.event_detector import EventDetector
from backend.services.mjpeg_client import MjpegClient
from backend.services.output_builder import build_enriched_output
from backend.services.persistence_worker import PersistenceWorker
from backend.services.serial_manager import SerialManager
from backend.services.telemetry_store import TelemetryStore

load_dotenv()  # no-op si no existe .env

# Configurado a nivel de modulo (no solo en el bloque __main__) porque
# `uvicorn backend.app:app` importa este archivo sin pasar por __main__:
# sin esto, los logs INFO de todo el backend (arranque de workers,
# conexiones de panel, etc.) se pierden en silencio y solo se ven los
# WARNING/ERROR sueltos que Python emite via su handler de ultimo recurso,
# sin timestamp ni nombre de logger.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)

USE_MOCK = os.environ.get("UKUCHA_USE_MOCK", "1") != "0"
TELEMETRY_PORT = int(os.environ.get("UKUCHA_TELEMETRY_PORT", "5002"))
CONTROL_PORT = int(os.environ.get("UKUCHA_CONTROL_PORT", "4210"))
CAM_URL = os.environ.get("UKUCHA_CAM_URL", "http://192.168.4.1/")
ENV_EVERY = int(os.environ.get("UKUCHA_ENV_EVERY", "5"))

# Topologia actual: un unico ESP32-S3 de campo (ver
# .claude/skills/ukucha/backend-conexion.md). El paquete de telemetria no
# trae node_id propio (schemas/uplink.py), asi que se etiqueta aca con un
# identificador fijo -- si en el futuro hay mas de un nodo, esto pasa a
# derivarse de la IP de origen (ver UdpTransport._node_ip).
FIELD_NODE_ID = "esp32s3_campo"

# Telemetria real llega a 10Hz -- loguear 1 de cada N paquetes para poder
# seguirla a ojo por terminal (ver plan de visualizacion sin frontend).
_TELEMETRY_LOG_EVERY = 10


def _build_persistence_backend() -> PersistenceBackend:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        logger.warning(
            "SUPABASE_URL/SUPABASE_KEY no configurados: persistencia usa "
            "NullPersistenceAdapter (no se guarda nada, el resto del backend "
            "funciona igual). Ver env.example para configurar Supabase."
        )
        return NullPersistenceAdapter()
    try:
        from backend.adapters.supabase_adapter import SupabaseAdapter
        return SupabaseAdapter(url=url, key=key)
    except Exception as e:
        logger.error(
            "No se pudo inicializar SupabaseAdapter (%s); se usa NullPersistenceAdapter", e
        )
        return NullPersistenceAdapter()


def _warmup(detection_service: DetectionService) -> None:
    """Corre un frame dummy al arrancar para absorber el JIT de CUDA
    (~5s medidos en Fase 3) antes de que llegue el primer frame real."""
    dummy = np.zeros((120, 160, 3), dtype=np.uint8)
    ok, buf = cv2.imencode(".jpg", dummy)
    if ok:
        detection_service.process_jpeg(-1, buf.tobytes(), 0)
        logger.info("Pipeline de deteccion precalentado")


def _safe_put(q: "asyncio.Queue", item) -> None:
    try:
        q.put_nowait(item)
    except asyncio.QueueFull:
        logger.warning(
            "Cola de salida WS llena, se descarta frame_id=%s", getattr(item, "frame_id", "?")
        )


async def _broadcast_loop(app: FastAPI) -> None:
    while True:
        output = await app.state.output_queue.get()
        payload = output.model_dump_json(by_alias=True)
        for ws in list(app.state.stream_clients):
            try:
                await ws.send_text(payload)
            except Exception:
                app.state.stream_clients.discard(ws)


def create_app() -> FastAPI:
    telemetry_store = TelemetryStore()
    detection_service = DetectionService(env_every=ENV_EVERY)
    _warmup(detection_service)

    persistence_backend = _build_persistence_backend()
    persistence_worker = PersistenceWorker(persistence_backend)
    event_detector = EventDetector()

    def _on_detection_result(result: dict) -> None:
        try:
            output = build_enriched_output(result, telemetry_store)
        except Exception:
            logger.exception(
                "build_enriched_output fallo para frame_id=%s", result.get("frame_id")
            )
            return

        for event in event_detector.detect(output):
            logger.info("EVENTO DETECTADO: %s (frame_id=%s)", event["tipo"], event["frame_id"])
            persistence_worker.save_event(event)

        loop = getattr(app.state, "loop", None)
        if loop is None:
            return
        loop.call_soon_threadsafe(_safe_put, app.state.output_queue, output)

    detection_worker = DetectionWorker(detection_service, on_result=_on_detection_result)

    # Video: el ESP32-CAM real sirve su propio stream HTTP MJPEG (canal WiFi
    # separado del enlace de sensores) -- no hay fragmentacion que reensamblar.
    if USE_MOCK:
        camera_source = MockCameraFeed(on_frame=detection_worker.submit_frame)
    else:
        camera_source = MjpegClient(url=CAM_URL, on_frame=detection_worker.submit_frame)

    # send_fn referencia serial_manager, definido mas abajo -- valido porque
    # el lambda solo se ejecuta despues de que serial_manager ya exista
    # (recien cuando el panel dispare un comando, tras el arranque completo).
    command_service = CommandService(
        send_fn=lambda cmd: serial_manager.send_command(cmd),
        on_log=persistence_worker.save_command_log,
        target_node=FIELD_NODE_ID,
    )

    packet_count = 0

    def _on_packet(packet: TelemetryPacket) -> None:
        nonlocal packet_count
        packet_count += 1
        # Telemetria llega a 10Hz -- se loguea 1 de cada N para poder seguirla
        # a ojo por terminal (sin frontend) sin saturar la consola.
        if packet_count % _TELEMETRY_LOG_EVERY == 0:
            logger.info(
                "Telemetria: audio=(%s,%s) gas=(mq7=%s,mq136=%s) pir=%s "
                "gps=(%s,%s) clima=(%sC,%shPa,%s%%)",
                packet.audio.vol_l, packet.audio.vol_r,
                packet.gas.mq1, packet.gas.mq2, packet.pir_detected,
                packet.gps.lat, packet.gps.lon,
                packet.climate.temp_c, packet.climate.pressure_hpa, packet.climate.humidity_pct,
            )
        telemetry_store.update(packet)
        persistence_worker.save_telemetry({
            "kind": "telemetry",
            "node_id": FIELD_NODE_ID,
            "timestamp_ms": int(time.time() * 1000),
            "data": packet.model_dump(),
        })

    transport = MockTransport() if USE_MOCK else UdpTransport(
        listen_port=TELEMETRY_PORT, control_port=CONTROL_PORT,
    )
    serial_manager = SerialManager(transport=transport, on_packet=_on_packet)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.loop = asyncio.get_running_loop()
        persistence_worker.start()
        detection_worker.start()
        camera_source.start()
        serial_manager.start()
        broadcast_task = asyncio.create_task(_broadcast_loop(app))
        logger.info(
            "Backend UKUCHA arriba (sensores=%s, camara=%s, persistencia=%s)",
            "MockTransport" if USE_MOCK else f"UDP:{TELEMETRY_PORT}/{CONTROL_PORT}",
            "MockCameraFeed" if USE_MOCK else CAM_URL,
            type(persistence_backend).__name__,
        )
        try:
            yield
        finally:
            broadcast_task.cancel()
            serial_manager.stop()
            camera_source.stop()
            detection_worker.stop()
            persistence_worker.stop()
            detection_service.close()
            logger.info("Backend UKUCHA detenido")

    app = FastAPI(title="UKUCHA Backend v2", version="0.2.0", lifespan=lifespan)
    cors_origins = [
        origin.strip()
        for origin in os.environ.get("CORS_ORIGINS", "*").split(",")
        if origin.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.stream_clients = set()
    app.state.output_queue = asyncio.Queue(maxsize=4)
    app.state.command_service = command_service

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok"}

    app.include_router(stream_router)
    app.include_router(commands_router)
    return app


app = create_app()


if __name__ == "__main__":
    import json
    import time as _time

    from starlette.testclient import TestClient

    with TestClient(app) as client:
        with client.websocket_connect("/ws/stream") as stream_ws, \
             client.websocket_connect("/ws/commands") as cmd_ws:

            cmd_ws.send_json({
                "command": "set_actuators",
                "params": {"luces": 1, "motor_a": 0, "motor_b": 0},
            })
            ack = cmd_ws.receive_json()
            logger.info("Respuesta del canal de comandos: %s", ack)

            logger.info("Esperando frames enriquecidos por /ws/stream...")
            received = 0
            deadline = _time.monotonic() + 10.0
            while received < 3 and _time.monotonic() < deadline:
                msg = stream_ws.receive_text()
                data = json.loads(msg)
                logger.info(
                    "Frame %s: detections=%d fall.hay_alerta=%s audio.stale=%s env.stale=%s",
                    data["frame_id"], len(data["detections"]),
                    data["fall"]["hay_alerta"], data["audio"]["stale"], data["env"]["stale"],
                )
                received += 1

            if received == 0:
                logger.error("No se recibio ningun frame por /ws/stream")
            else:
                logger.info("Fase 4 verificada: %d frames recibidos por WebSocket", received)

    # --- Verificacion directa de EventDetector ---
    # MockCameraFeed genera ruido sintetico sin personas/escombros reales,
    # asi que nunca dispara una alerta organicamente. Se prueba la logica
    # de borde (transicion False->True, sin repetir mientras se mantiene
    # True) construyendo una salida enriquecida sintetica a mano.
    from backend.schemas.output import (
        AudioState, EnrichedFrameOutput, EnvState, EppInfo, FallInfo, FusionInfo,
    )
    from backend.services.event_detector import EventDetector as _EventDetector

    logger.info("Verificando logica de borde de EventDetector...")
    detector = _EventDetector()
    fake_output = EnrichedFrameOutput(
        frame_id=999, timestamp="2026-01-01T00:00:00Z", image_b64="", detections=[],
        fall=FallInfo(hay_alerta=True, hay_critica=False, n_personas=1),
        epp=EppInfo(n_victims=0, n_rescuer=0, n_epp=0),
        fusion=FusionInfo(n_rubble_victims=0, n_fall_rubble=0, n_risk_zones=0, n_civilians=0, n_routes=0),
        audio=AudioState(stale=True), env=EnvState(stale=True),
    )
    events_1 = detector.detect(fake_output)
    events_2 = detector.detect(fake_output)
    logger.info(
        "EventDetector: primer frame -> %d evento(s) [%s], segundo frame igual -> %d evento(s) (debe ser 0)",
        len(events_1), events_1[0]["tipo"] if events_1 else "-", len(events_2),
    )
    assert len(events_1) == 1 and events_1[0]["tipo"] == "caida_detectada", "borde de subida no disparo"
    assert len(events_2) == 0, "el evento se repitio sin una nueva transicion"
    logger.info("Verificacion de edge-detection de EventDetector correcta")
