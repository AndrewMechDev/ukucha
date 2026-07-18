"""Paquetes de subida (nodo -> PC) que llegan por el enlace serial full-duplex.

Union discriminada por packet_type: cualquier linea JSON invalida o de un
tipo no reconocido falla la validacion de forma explicita (ValidationError),
en vez de aceptarse silenciosamente con campos faltantes.
"""
from __future__ import annotations

from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Field, TypeAdapter


class FramePacket(BaseModel):
    node_id: str
    timestamp_ms: int
    packet_type: Literal["frame"]
    frame_id: int
    seq: int
    seq_total: int
    payload_b64: str


class AudioSensorsData(BaseModel):
    mic1_db: float
    mic2_db: float


class AudioSensorsPacket(BaseModel):
    node_id: str
    timestamp_ms: int
    packet_type: Literal["audio_sensors"]
    data: AudioSensorsData


class GpsData(BaseModel):
    lat: float
    lon: float
    fix: bool
    sats: int


class DustData(BaseModel):
    pm1_0: int
    pm2_5: int
    pm10: int


class GasReading(BaseModel):
    raw_adc: int
    ppm_est: Optional[float] = None  # null mientras no haya curva de calibracion Rs/Ro lista


class MotorsState(BaseModel):
    m1: int
    m2: int
    m3: int
    m4: int


class EnvActuationData(BaseModel):
    gps: GpsData
    tof_distance_mm: int
    dust_pms5003: DustData
    gas_mq7_co: GasReading
    gas_mq136_h2s: GasReading
    led_state: str
    motors: MotorsState
    battery_v: float
    gyro: Optional[dict] = None  # reservado para giroscopio futuro, hoy siempre null


class EnvActuationPacket(BaseModel):
    node_id: str
    timestamp_ms: int
    packet_type: Literal["env_and_actuation"]
    data: EnvActuationData


class CmdAckPacket(BaseModel):
    """Confirmacion de un comando de bajada, identificado por cmd_id.

    Este packet_type NO esta confirmado en el firmware al momento de escribir
    este modulo (ver decision de arquitectura en feature/conexion): se asume
    que ESP32-S3 No3 lo emitira a futuro. El backend ya sabe parsearlo para
    no requerir cambios cuando el firmware lo implemente; mientras tanto,
    SerialManager solo loguea "enviado" + timeout sin bloquear nada.
    """

    node_id: str
    timestamp_ms: int
    packet_type: Literal["cmd_ack"]
    cmd_id: int
    status: Literal["ok", "error"] = "ok"


UplinkPacket = Annotated[
    Union[FramePacket, AudioSensorsPacket, EnvActuationPacket, CmdAckPacket],
    Field(discriminator="packet_type"),
]

uplink_adapter: TypeAdapter = TypeAdapter(UplinkPacket)
