"""Pydantic models de la salida enriquecida hacia el panel web (WebSocket).

Esquema EXTENDIDO respecto al ejemplo generico del prompt original: en vez
de aplanar todo a una lista de {class, confidence, bbox}, se preserva la
estructura de fusion de 6 escenarios que ya produce el pipeline (fall/epp/
fusion). El array `detections` se mantiene como subconjunto plano derivado
-- compat con integraciones simples del panel -- pero NO es la fuente de
verdad; los conteos ricos viven en los campos anidados.

`AudioState`/`EnvState` reflejan el paquete de telemetria real del ESP32-S3
de campo (ver schemas/uplink.py::TelemetryPacket), no el diseño original
especulativo: sin ToF/gyro/led_state/motors reportados (el hardware real
no los tiene o son de solo escritura), con `climate` (temp/presion/humedad)
que si existe en el firmware real.
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

from backend.schemas.uplink import ClimateReading, GasLevels, GpsFix


class Detection(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    class_: str = Field(alias="class")
    confidence: Optional[float] = None  # None cuando la deteccion origen no trae confianza
    bbox: List[float]


class FallInfo(BaseModel):
    hay_alerta: bool
    hay_critica: bool
    n_personas: int


class EppInfo(BaseModel):
    n_victims: int
    n_rescuer: int
    n_epp: int


class FusionInfo(BaseModel):
    n_rubble_victims: int
    n_fall_rubble: int
    n_risk_zones: int
    n_civilians: int
    n_routes: int


class AudioState(BaseModel):
    vol_l: Optional[float] = None
    vol_r: Optional[float] = None
    stale: bool


class EnvState(BaseModel):
    gps: Optional[GpsFix] = None
    gas: Optional[GasLevels] = None  # mq1/mq2 en None hasta que se conecten los sensores fisicos
    dust_ppm: Optional[float] = None  # None hasta que se conecte el sensor de polvo
    climate: Optional[ClimateReading] = None
    stale: bool


class EnrichedFrameOutput(BaseModel):
    frame_id: int
    timestamp: str  # ISO 8601 UTC
    image_b64: str  # data:image/jpeg;base64,...
    detections: List[Detection]
    fall: FallInfo
    epp: EppInfo
    fusion: FusionInfo
    audio: AudioState
    env: EnvState
