"""Paquete de telemetria de subida (ESP32-S3 de campo -> PC) real.

Llega por UDP (puerto 5002 por defecto) como una linea de texto plano
delimitada por pipes -- NO es JSON con packet_type discriminador como se
asumio en el diseño original migrado desde test-yolo:

    A:<vol_l>,<vol_r>|M:<mq7>,<mq136>|P:<pir>|G:<lat>,<lon>|C:<temp>,<presion>,<humedad>

Fuente de verdad: appflores/esp32s3_firmware.ino (TaskTelemetry, linea
"Formato: A:%.1f,%.1f|M:%d,%d|P:%d|G:%.6f,%.6f|C:%.2f,%.2f,%.2f").

Diferencias confirmadas contra el diseño original (ver .claude/skills/
ukucha/backend-conexion.md, seccion "Gaps y decisiones conocidas"):
- Topologia real: 1 solo ESP32-S3 de campo habla WiFi/UDP directo al PC
  (no hay 3 nodos S3 + dongle ESP-NOW por serial).
- No hay ToF, giroscopio, `led_state` reportado, ni 4 motores -- el
  hardware solo expone 2 motores + 1 canal de luces, y son de solo
  escritura (ver downlink.py), nunca se leen de vuelta.
- GPS solo trae lat/lon (TinyGPS++ expone fix/sats pero el firmware
  todavia no los serializa).
- Gas (MQ7/MQ136, seccion `M:`): sensores fisicos ya conectados, valores
  ADC crudos (`analogRead`, 0-4095) reales, no un placeholder.
- Presencia (seccion `P:`): el firmware **ya NO manda PM2.5/polvo** --
  ese sensor se saco del diseño. `P:` ahora es el HC-SR501 (PIR), lectura
  digital `0`/`1` de `digitalRead`. Si un consumidor viejo de este modulo
  todavia espera `dust_ppm`, esta desactualizado: el campo se renombro a
  `pir_detected` (bool) porque es una cantidad fisica distinta, no la
  misma con otro nombre.
- Clima (temperatura/presion/humedad, BMP280+AHT20) SI existe en el
  firmware real y no estaba contemplado en el esquema original.
"""
from __future__ import annotations

import logging
from typing import Optional

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)


class AudioLevels(BaseModel):
    """Envolvente de volumen I2S en % (0-100), no dB -- ver TaskAudio en
    esp32s3_firmware.ino (constrain(avg/12000*100, 0, 100))."""

    vol_l: float
    vol_r: float


class GasLevels(BaseModel):
    """mq1 (CO, MQ7) / mq2 (H2S, MQ136): lectura ADC cruda (analogRead,
    0-4095), sin calibrar a ppm -- el firmware no hace esa conversion."""

    mq1: Optional[float] = None
    mq2: Optional[float] = None


class GpsFix(BaseModel):
    """Solo lat/lon por ahora -- fix/sats pendientes de agregar al firmware."""

    lat: Optional[float] = None
    lon: Optional[float] = None


class ClimateReading(BaseModel):
    """AHT20 (temp/humedad) + BMP280 (presion, y respaldo de temp)."""

    temp_c: Optional[float] = None
    pressure_hpa: Optional[float] = None
    humidity_pct: Optional[float] = None


class TelemetryPacket(BaseModel):
    """Un paquete de telemetria completo del ESP32-S3 de campo (~10Hz).

    Sin node_id/timestamp_ms propios (el firmware no los incluye en la
    linea); quien reciba el paquete (UdpTransport/SerialManager) le agrega
    el momento de recepcion."""

    audio: AudioLevels
    gas: GasLevels
    pir_detected: Optional[bool] = None  # HC-SR501, digitalRead 0/1 (seccion P:)
    gps: GpsFix
    climate: ClimateReading

    @classmethod
    def from_line(cls, text: str) -> "TelemetryPacket":
        """Parsea 'A:l,r|M:mq7,mq136|P:pir|G:lat,lon|C:t,p,h'.

        Lanza ValueError si falta una seccion completa o el separador
        interno de una seccion no tiene la cantidad esperada de valores --
        nunca acepta silenciosamente una linea truncada."""
        sections: dict[str, str] = {}
        for part in text.split("|"):
            if ":" not in part:
                raise ValueError(f"Seccion sin prefijo valido: {part!r}")
            key, _, value = part.partition(":")
            sections[key] = value

        missing = {"A", "M", "P", "G", "C"} - sections.keys()
        if missing:
            raise ValueError(f"Faltan secciones {sorted(missing)} en linea: {text!r}")

        vol_l_raw, vol_r_raw = _split(sections["A"], 2, "A")
        mq1_raw, mq2_raw = _split(sections["M"], 2, "M")
        lat_raw, lon_raw = _split(sections["G"], 2, "G")
        temp_raw, press_raw, hum_raw = _split(sections["C"], 3, "C")

        vol_l = _parse_float(vol_l_raw)
        vol_r = _parse_float(vol_r_raw)
        if vol_l is None or vol_r is None:
            raise ValueError(f"Seccion A (audio) con valores invalidos: {sections['A']!r}")

        return cls(
            audio=AudioLevels(vol_l=vol_l, vol_r=vol_r),
            gas=GasLevels(mq1=_parse_float(mq1_raw), mq2=_parse_float(mq2_raw)),
            pir_detected=_parse_bool_flag(sections["P"]),
            gps=GpsFix(lat=_parse_float(lat_raw), lon=_parse_float(lon_raw)),
            climate=ClimateReading(
                temp_c=_parse_float(temp_raw),
                pressure_hpa=_parse_float(press_raw),
                humidity_pct=_parse_float(hum_raw),
            ),
        )


def _split(raw: str, expected: int, section: str) -> list[str]:
    parts = raw.split(",")
    if len(parts) != expected:
        raise ValueError(
            f"Seccion {section} esperaba {expected} valores separados por coma, "
            f"recibio {len(parts)}: {raw!r}"
        )
    return parts


def _parse_bool_flag(raw: str) -> Optional[bool]:
    """El HC-SR501 manda digitalRead crudo ('0'/'1'). None si la seccion
    llega vacia o con un valor no numerico, en vez de asumir 'sin deteccion'."""
    value = _parse_float(raw)
    if value is None:
        return None
    return value != 0.0


def _parse_float(raw: str) -> Optional[float]:
    """El firmware puede enviar 'nan' (lectura invalida, ver
    appflores/registro_telemetria.csv) -- se normaliza a None en vez de
    fallar toda la linea por un solo campo fuera de rango."""
    try:
        value = float(raw)
    except ValueError:
        return None
    if value != value:  # NaN != NaN
        return None
    return value


def parse_telemetry_line(text: str) -> Optional[TelemetryPacket]:
    """Punto de entrada usado por SerialManager (via cualquier Transport,
    serial o UDP). None (con warning logueado) si la linea no se pudo
    parsear, en vez de propagar la excepcion al hilo lector."""
    try:
        return TelemetryPacket.from_line(text)
    except (ValueError, ValidationError) as e:
        logger.warning("Linea de telemetria invalida, descartada: %s (%s)", text[:200], e)
        return None
