"""app.py — arma el backend UKUCHA completo: enlace serial full-duplex,
reensamblado de frames, deteccion (caidas + EPP + escombros + fusion),
telemetria con staleness, comandos con cmd_id/ack, y persistencia no
bloqueante (Supabase o NullPersistenceAdapter), expuesto via FastAPI
(WebSocket + REST).

Config por variable de entorno (todas opcionales; sin ninguna, el backend
arranca en modo desarrollo completo: MockTransport + sin persistencia real):
    UKUCHA_USE_MOCK=1        usar MockTransport en vez del puerto serial real
    UKUCHA_SERIAL_PORT=COM3  puerto real (ignorado si UKUCHA_USE_MOCK=1)
    UKUCHA_BAUDRATE=115200
    UKUCHA_ENV_EVERY=5       correr RescueDetector 1 de cada N frames
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
from contextlib import asynccontextmanager

import cv2
import numpy as np
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.adapters.mock_transport import MockTransport
from backend.adapters.null_adapter import NullPersistenceAdapter
from backend.adapters.serial_transport import SerialTransport
from backend.api.ws_commands import router as commands_router
from backend.api.ws_stream import router as stream_router
from backend.ports.persistence import PersistenceBackend
from backend.schemas.uplink import (
    AudioSensorsPacket,
    CmdAckPacket,
    EnvActuationPacket,
    FramePacket,
    UplinkPacket,
)
from backend.services.command_service import CommandService
from backend.services.detection_service import DetectionService
from backend.services.detection_worker import DetectionWorker
from backend.services.event_detector import EventDetector
from backend.services.frame_reassembler import FrameReassembler
from backend.services.output_builder import build_enriched_output
from backend.services.persistence_worker import PersistenceWorker
from backend.services.serial_manager import SerialManager
from backend.services.telemetry_store import TelemetryStore

load_dotenv()  # no-op si no existe .env

logger = logging.getLogger(__name__)

USE_MOCK = os.environ.get("UKUCHA_USE_MOCK", "1") != "0"
SERIAL_PORT = os.environ.get("UKUCHA_SERIAL_PORT", "COM3")
BAUDRATE = int(os.environ.get("UKUCHA_BAUDRATE", "115200"))
ENV_EVERY = int(os.environ.get("UKUCHA_ENV_EVERY", "5"))


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
            persistence_worker.save_event(event)

        loop = getattr(app.state, "loop", None)
        if loop is None:
            return
        loop.call_soon_threadsafe(_safe_put, app.state.output_queue, output)

    detection_worker = DetectionWorker(detection_service, on_result=_on_detection_result)
    reassembler = FrameReassembler(on_frame_complete=detection_worker.submit_frame)

    # send_fn referencia serial_manager, definido mas abajo -- valido porque
    # el lambda solo se ejecuta despues de que serial_manager ya exista
    # (recien cuando el panel dispare un comando, tras el arranque completo).
    command_service = CommandService(
        send_fn=lambda cmd: serial_manager.send_command(cmd),
        on_log=persistence_worker.save_command_log,
    )

    def _on_packet(packet: UplinkPacket) -> None:
        if isinstance(packet, FramePacket):
            reassembler.add_chunk(packet)
        elif isinstance(packet, AudioSensorsPacket):
            telemetry_store.update_audio(packet)
            persistence_worker.save_telemetry({
                "kind": "audio_sensors", "node_id": packet.node_id,
                "timestamp_ms": packet.timestamp_ms,
                "data": packet.data.model_dump(),
            })
        elif isinstance(packet, EnvActuationPacket):
            telemetry_store.update_env(packet)
            persistence_worker.save_telemetry({
                "kind": "env_and_actuation", "node_id": packet.node_id,
                "timestamp_ms": packet.timestamp_ms,
                "data": packet.data.model_dump(),
            })
        elif isinstance(packet, CmdAckPacket):
            command_service.on_ack(packet.cmd_id, packet.status)

    transport = MockTransport() if USE_MOCK else SerialTransport(port=SERIAL_PORT, baudrate=BAUDRATE)
    serial_manager = SerialManager(transport=transport, on_packet=_on_packet)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.loop = asyncio.get_running_loop()
        persistence_worker.start()
        reassembler.start()
        detection_worker.start()
        serial_manager.start()
        broadcast_task = asyncio.create_task(_broadcast_loop(app))
        logger.info(
            "Backend UKUCHA arriba (fuente=%s, persistencia=%s)",
            "MockTransport" if USE_MOCK else f"serial:{SERIAL_PORT}",
            type(persistence_backend).__name__,
        )
        try:
            yield
        finally:
            broadcast_task.cancel()
            serial_manager.stop()
            detection_worker.stop()
            reassembler.stop()
            persistence_worker.stop()
            detection_service.close()
            logger.info("Backend UKUCHA detenido")

    app = FastAPI(title="UKUCHA Backend v2", version="0.2.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.stream_clients = set()
    app.state.output_queue = asyncio.Queue(maxsize=4)
    app.state.command_service = command_service

    app.include_router(stream_router)
    app.include_router(commands_router)
    return app


app = create_app()


if __name__ == "__main__":
    import json
    import time as _time

    from starlette.testclient import TestClient

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    with TestClient(app) as client:
        with client.websocket_connect("/ws/stream") as stream_ws, \
             client.websocket_connect("/ws/commands") as cmd_ws:

            cmd_ws.send_json({"command": "set_leds", "params": {"pattern": "red_solid"}})
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

    # --- Fase 5: verificacion directa de EventDetector ---
    # MockTransport genera ruido sintetico sin personas/escombros reales,
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
    logger.info("Fase 5 verificada: edge-detection de EventDetector correcta")
