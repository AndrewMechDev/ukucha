"""Construye EnrichedFrameOutput a partir del dict crudo de
DetectionService.process_jpeg() y el ultimo estado conocido de telemetria
(TelemetryStore). Es el unico lugar donde se aplana la fusion rica a la
lista `detections` de compatibilidad -- ver nota en schemas/output.py.
"""
from __future__ import annotations

import base64
from datetime import datetime, timezone

from backend.schemas.output import (
    AudioState,
    Detection,
    EnrichedFrameOutput,
    EnvState,
    EppInfo,
    FallInfo,
    FusionInfo,
)
from backend.services.telemetry_store import TelemetryStore


def build_enriched_output(result: dict, telemetry_store: TelemetryStore) -> EnrichedFrameOutput:
    detections: list[Detection] = []

    for persona in result["fall"]["personas"]:
        if persona["estado"] in ("EN EL SUELO", "CAYENDO"):
            detections.append(Detection(
                class_="persona_caida", confidence=persona["score"], bbox=list(persona["bbox"]),
            ))

    for _tid, bbox, confirmable in result["epp"]["victims"]:
        cls = "victima" if confirmable else "indicio_persona"
        detections.append(Detection(class_=cls, confidence=None, bbox=list(bbox)))

    for _name, hbox, hconf in result["env"]["hazards"]:
        detections.append(Detection(class_="escombro", confidence=hconf, bbox=list(hbox)))

    for _name, cbox, cconf in result["env"]["civilians"]:
        detections.append(Detection(class_="civil", confidence=cconf, bbox=list(cbox)))

    for _name, bbox, bconf in result["env"]["blocked"]:
        detections.append(Detection(class_="acceso_bloqueado", confidence=bconf, bbox=list(bbox)))

    for _name, rbox, rconf in result["env"]["rescue_teams"]:
        detections.append(Detection(class_="equipo_rescate", confidence=rconf, bbox=list(rbox)))

    audio = telemetry_store.get_audio()
    env = telemetry_store.get_env()

    image_b64 = "data:image/jpeg;base64," + base64.b64encode(result["annotated_jpeg"]).decode("ascii")

    return EnrichedFrameOutput(
        frame_id=result["frame_id"],
        timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        image_b64=image_b64,
        detections=detections,
        fall=FallInfo(
            hay_alerta=result["fall"]["hay_alerta"],
            hay_critica=result["fall"]["hay_critica"],
            n_personas=len(result["fall"]["personas"]),
        ),
        epp=EppInfo(
            n_victims=len(result["epp"]["victims"]),
            n_rescuer=result["epp"]["n_rescuer"],
            n_epp=result["epp"]["n_epp"],
        ),
        fusion=FusionInfo(
            n_rubble_victims=len(result["fusion"]["rubble_victims"]),
            n_fall_rubble=result["fusion"]["n_fall_rubble"],
            n_risk_zones=result["fusion"]["n_risk_zones"],
            n_civilians=result["fusion"]["n_civilians"],
            n_routes=result["fusion"]["n_routes"],
        ),
        audio=AudioState(**audio),
        env=EnvState(**env),
    )
