# Skill: UKUCHA Backend v2 — Enlace Serial + Deteccion + WebSocket + Persistencia

## ACTUALIZACION — hardware real confirmado (rama `feature/backend`, ukucha)

Todo el diseño original de este documento (secciones de abajo) se escribio
**antes** de tener firmware/hardware confirmado, como el propio documento
ya advertia en "Gaps y decisiones conocidas" (`CmdAckPacket` no confirmado).
Al integrar el codigo real del compañero de hardware (`appflores/`:
`server.js`, `record_serial.js`, `esp32s3_firmware.ino`,
`esp32cam_firmware.ino`) se confirmaron varias divergencias. **El diseño
de abajo queda como contexto historico de arquitectura (Ports & Adapters
sigue vigente), pero los detalles de protocolo/topologia estan
desactualizados.** La fuente de verdad actual es el codigo en
`backend/schemas/uplink.py`, `backend/schemas/downlink.py`,
`backend/adapters/udp_transport.py` y `backend/services/mjpeg_client.py`.

Divergencias confirmadas:

| Tema | Diseño original (abajo) | Hardware real |
|---|---|---|
| Topologia | ESP32-CAM + 3x ESP32-S3 + dongle No3 (ESP-NOW -> serial USB) | ESP32-CAM (video) + 1x ESP32-S3 de campo (sensores), ambos WiFi directo |
| Transporte de sensores | `SerialTransport` (pyserial, `COM3`) | `UdpTransport`: UDP entrante `:5002` (telemetria), UDP saliente `:4210` (comandos) — IP del nodo autodetectada del primer paquete |
| Formato de paquete | JSON con `packet_type` discriminador | Texto plano pipe-delimited: `A:volL,volR\|M:mq7,mq136\|P:pir\|G:lat,lon\|C:temp,presion,humedad` (`TelemetryPacket.from_line`) |
| Video | `FramePacket` fragmentado + `FrameReassembler` sobre el mismo enlace | Stream HTTP MJPEG propio del ESP32-CAM (`multipart/x-mixed-replace`, puerto 80) leido por `MjpegClient` — `FrameReassembler` se elimino del repo |
| Comandos | JSON `{target_node, cmd_id, command, params}` con ack (`CmdAckPacket`) | Texto plano `C:<luces>,<motorA>,<motorB>` sin ack (`ControlCommand.to_wire()`); un solo comando `set_actuators` |
| GPS | `{lat, lon, fix, sats}` | Solo `{lat, lon}` (`GpsFix`) — fix/sats pendientes en el firmware |
| Gas (MQ7/MQ136) | `{raw_adc, ppm_est}` | Valores planos `mq1, mq2` (`GasLevels`), **sensores fisicos ya conectados**, ADC crudo (0-4095) sin calibrar a ppm |
| Polvo (PMS5003) | `{pm1_0, pm2_5, pm10}` | **Se dio de baja del diseño** -- no hay sensor de polvo en el hardware real. El slot `P:` del wire format se reuso para el HC-SR501 (PIR) |
| Presencia (PIR) | No existia en el esquema | `pir_detected: Optional[bool]` (`P:` = `digitalRead` del HC-SR501, 0/1) -- **no confundir con el polvo que ocupaba antes ese mismo slot del wire format** |
| Clima | No existia en el esquema | `ClimateReading` (temp/presion/humedad, BMP280+AHT20) — SI existe en el firmware real |
| ToF, gyro, `led_state`, 4 motores | Declarados en el esquema | No existen en el firmware; hay 1 tira NeoPixel (vumetro, no controlable por comando) + 2 motores + `luces`, ambos de solo escritura |

Actualizacion de hardware (segunda ronda): se sumaron sensores fisicos MQ7
(CO), MQ136 (H2S) y HC-SR501 (PIR de presencia). El polvo/PM2.5 se dio de
baja del diseño -- no hay sensor fisico para eso. Pendiente: la mejora de
precision del GPS (fix/sats), que se implementara en el firmware mas
adelante — mientras tanto llega solo `{lat, lon}` y el resto del pipeline
(deteccion, WS, persistencia) funciona igual.

### Confirmacion definitiva: no hay ni va a haber USB

El compañero de hardware confirmo que la conexion es **100% WiFi,
permanente** — no es un estado transitorio del prototipo, no hay plan de
volver a un enlace serial USB en ningun momento. Por eso:

- `backend/adapters/serial_transport.py` (el adapter de `pyserial`/`COM3`
  de la Fase 1 original) se conserva en el repo **solo como referencia
  historica**, marcado explicitamente como sin uso en su propio docstring.
  `app.py` nunca lo importa. Su `import serial` es perezoso (adentro de
  cada metodo) para que el archivo se pueda seguir importando sin que
  `pyserial` este instalado.
- `pyserial` se saco de `requirements.txt` — ya no es una dependencia real
  del backend.
- Todas las menciones de `SerialTransport`/`COM3`/`UKUCHA_SERIAL_PORT` en
  las secciones de abajo (diseño original, Fase 1) son **puramente
  historicas**: no reflejan una opcion configurable disponible hoy.

**Topologia de red real**: el ESP32-CAM y el ESP32-S3 de campo no arman su
propio Access Point — se conectan como clientes a **la misma red WiFi que
genera el hotspot del celular** (no un router fijo). Implicancias
practicas:

- La IP de cada nodo la asigna el DHCP del hotspot y **puede cambiar entre
  sesiones** (se corta el hotspot, se reconecta el telefono, etc.) — por
  eso `UdpTransport` ya autodetecta la IP del ESP32-S3 del primer paquete
  recibido ([udp_transport.py:75-80](../../../backend/adapters/udp_transport.py)),
  no hace falta tocar nada ahi.
- `UKUCHA_CAM_URL` (default `http://192.168.4.1/` en `env.example`) **si
  hay que actualizarlo a mano cada sesion**: ese default asume que el
  ESP32-CAM es su propio AP (IP fija tipica de ESP32 en modo AP), pero con
  hotspot del celular el ESP32-CAM va a tener una IP DHCP distinta —
  revisar la lista de dispositivos conectados del hotspot (o el firmware,
  si loguea su IP por serial de debug) para saber cual usar.
- La PC/laptop que corre el backend tambien tiene que estar conectada a
  ese mismo hotspot (misma subred), no a la red WiFi habitual — sino
  `UdpTransport` nunca va a recibir los paquetes UDP de telemetria.
- El firmware del ESP32-S3 (`hostIp` en `esp32s3_firmware.ino`, no
  trackeado en git) tiene **hardcodeada la IP de la laptop** a la que le
  manda los paquetes UDP -- es la misma caveat que `UKUCHA_CAM_URL` pero
  al reves: si el hotspot le reasigna a la laptop una IP distinta en una
  sesion futura (reinicio de telefono, etc.), hay que re-flashear (o
  agregar autodescubrimiento, que hoy no existe del lado del firmware)
  con la IP nueva, sino el ESP32-S3 va a seguir mandando paquetes a una
  IP que ya no es la laptop y `UdpTransport` no va a recibir nada.

## Objetivo (diseño original, ver seccion de arriba para el estado real)

`backend/` es el servidor de tiempo real que reemplaza el flujo webcam del
detector original (`webcam_fall.py`) por una tuberia de hardware de 4 nodos:

- **ESP32-CAM** — captura de video.
- **3x ESP32-S3** — sensores (audio/gases/GPS/polvo/ToF), actuadores (motores,
  LEDs) y el nodo **No3**, que actua de dongle: concentra todo el trafico
  ESP-NOW de los otros nodos y lo entrega a la PC por **un unico enlace serial
  full-duplex USB**.

El backend abre ese enlace serial, parsea los paquetes de subida
(frame fragmentado, audio, entorno/actuacion, ack de comandos), reensambla los
frames JPEG, corre el pipeline de vision completo (caidas + EPP + escombros +
fusion de 6 escenarios), enriquece cada frame con la ultima telemetria conocida,
lo retransmite a paneles web por WebSocket, acepta comandos de control remoto
(motores/LEDs/reinicio de camara) por WebSocket o REST, y persiste eventos
relevantes en Supabase de forma no bloqueante.

Se construyo en 5 fases incrementales:

| Fase | Que agrega | Archivos nuevos |
|---|---|---|
| 1 | Enlace serial full-duplex (Ports & Adapters) | `schemas/uplink.py`, `schemas/downlink.py`, `ports/transport.py`, `adapters/serial_transport.py`, `adapters/mock_transport.py`, `services/serial_manager.py` |
| 2 | Reensamblado de frames JPEG | `services/frame_reassembler.py` |
| 3 | Integracion del pipeline de deteccion | `services/detection_service.py` |
| 4 | Servidor WebSocket + canal de comandos | `schemas/output.py`, `services/telemetry_store.py`, `services/command_service.py`, `services/detection_worker.py`, `services/output_builder.py`, `api/deps.py`, `api/ws_stream.py`, `api/ws_commands.py`, `app.py` |
| 5 | Persistencia Supabase no bloqueante | `ports/persistence.py`, `adapters/null_adapter.py`, `adapters/supabase_adapter.py`, `services/persistence_worker.py`, `services/event_detector.py`, `supabase_schema.sql` |

Este documento permite regenerar el directorio `backend/` completo, identico,
desde cero.

### Patron de arquitectura: Ports & Adapters (Hexagonal-lite) + Service Layer

El backend NO es un MVT (Modelo-Vista-Template al estilo Django). Es
**Ports & Adapters** con una capa de servicios:

- **Ports** (`ports/`) — interfaces `Protocol` (structural typing de Python) que
  definen contratos: `Transport` (enlace fisico), `PersistenceBackend`
  (almacenamiento). La logica de negocio depende del Protocol, nunca de la
  implementacion concreta.
- **Adapters** (`adapters/`) — implementaciones intercambiables de esos ports:
  `SerialTransport`/`MockTransport` para `Transport`,
  `SupabaseAdapter`/`NullPersistenceAdapter` para `PersistenceBackend`.
- **Services** (`services/`) — la logica de negocio orquestadora
  (`SerialManager`, `FrameReassembler`, `DetectionService`, etc). No conoce
  pyserial ni Supabase; solo los ports.
- **API** (`api/` + `app.py`) — la capa de entrega FastAPI (WebSocket/REST) que
  cablea todo.

Por que este patron y no MVT: el nucleo del sistema es un **pipeline de tiempo
real orientado a datos** (hilos, colas, hardware), no un CRUD sobre una base de
datos con vistas HTML. Django MVT asume request-response HTTP sincrono sobre un
ORM; aca la fuente de verdad es un stream serial que empuja datos de forma
asincrona. FastAPI (ASGI + async nativo + Pydantic) encaja con Ports & Adapters
porque permite: (a) sustituir la fuente serial por un mock sin tocar YOLO ni el
WebSocket, (b) validar cada paquete con Pydantic en el borde, (c) correr la
inferencia pesada en hilos daemon fuera del event loop. El objetivo explicito
declarado en `ports/transport.py` es "reemplazar la fuente serial despues sin
tocar YOLO ni el WebSocket".

## Estructura del directorio

```
backend/
  __init__.py
  app.py                         # ensamblado FastAPI + lifespan + broadcast loop + smoke test __main__
  supabase_schema.sql            # DDL de las 3 tablas de persistencia (Fase 5)
  schemas/
    __init__.py
    uplink.py                    # paquetes nodo->PC (union discriminada por packet_type)
    downlink.py                  # DownlinkCommand (PC->nodo)
    output.py                    # EnrichedFrameOutput hacia el panel (esquema extendido, no plano)
  ports/
    __init__.py
    transport.py                 # Protocol Transport (enlace fisico full-duplex)
    persistence.py               # Protocol PersistenceBackend (almacenamiento)
  adapters/
    __init__.py
    serial_transport.py          # Transport sobre pyserial (hardware real)
    mock_transport.py            # Transport que simula ESP32-S3 No3 (dev sin hardware)
    supabase_adapter.py          # PersistenceBackend sobre Supabase
    null_adapter.py              # PersistenceBackend que solo loguea (default sin credenciales)
  services/
    __init__.py
    serial_manager.py            # hilo lector + escritura con lock + reconnect backoff
    frame_reassembler.py         # reensamblado de chunks JPEG + poda por timeout
    detection_service.py         # pipeline completo de vision sobre JPEG reensamblado
    detection_worker.py          # corre la inferencia en hilo dedicado, cola acotada drop-on-full
    telemetry_store.py           # ultimo estado de audio/env con marca de staleness
    command_service.py           # valida comandos, asigna cmd_id, trackea ack/timeout, on_log hook
    output_builder.py            # arma EnrichedFrameOutput a partir del dict crudo + telemetria
    event_detector.py            # edge-detection de eventos relevantes para persistir
    persistence_worker.py        # escribe a persistencia en hilo daemon, cola acotada no bloqueante
  api/
    __init__.py
    deps.py                      # dependencias FastAPI (get_command_service)
    ws_stream.py                 # WebSocket /ws/stream (salida de frames enriquecidos)
    ws_commands.py               # WebSocket /ws/commands + POST /api/commands (entrada de comandos)
```

Todos los `__init__.py` son archivos vacios (marcadores de paquete).

## Fase 1 — Enlace serial full-duplex

### `schemas/uplink.py` — paquetes de subida (nodo -> PC)

Union discriminada por `packet_type`: cualquier linea JSON invalida o de un tipo
no reconocido falla la validacion de forma explicita (`ValidationError`), en vez
de aceptarse silenciosamente con campos faltantes.

```python
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
```

Notas de diseño:

- Los 4 miembros comparten `node_id` y `timestamp_ms` como campos comunes. El
  discriminador es `packet_type` (`Literal`), lo que hace que Pydantic elija el
  modelo correcto y rechace tipos desconocidos.
- `GasReading.ppm_est` es `Optional[float] = None`: el firmware envia `raw_adc`
  siempre, y `ppm_est` solo cuando exista curva de calibracion Rs/Ro.
- `EnvActuationData.gyro` es `Optional[dict] = None`: reservado, hoy siempre null.
- `CmdAckPacket` **no esta confirmado en el firmware** al momento de escribir el
  modulo (decision de arquitectura en `feature/conexion`): se asume que No3 lo
  emitira a futuro. El backend ya sabe parsearlo para no requerir cambios cuando
  el firmware lo implemente; mientras tanto, `SerialManager` solo loguea el
  comando enviado + timeout sin bloquear nada.
- `uplink_adapter = TypeAdapter(UplinkPacket)` es el punto de entrada de
  validacion: `uplink_adapter.validate_python(dict)`.

### `schemas/downlink.py` — comandos de bajada (PC -> nodo)

```python
from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field


class DownlinkCommand(BaseModel):
    target_node: Literal["esp32_s3_no1", "esp32_s3_no2"]
    cmd_id: int
    command: str
    params: dict = Field(default_factory=dict)
```

`target_node` esta restringido a `esp32_s3_no1` / `esp32_s3_no2` (los nodos
actuadores; No3 es el dongle que reenvia, no un destino final).

### `ports/transport.py` — Protocol Transport

```python
from __future__ import annotations
from typing import Optional, Protocol


class Transport(Protocol):
    def open(self) -> None:
        """Abre el enlace. Debe ser idempotente si ya esta abierto."""
        ...

    def close(self) -> None:
        """Cierra el enlace. Debe ser idempotente si ya esta cerrado."""
        ...

    def readline(self) -> Optional[bytes]:
        """Lee una linea terminada en \\n. None si no hay datos dentro del
        timeout o si el enlace no esta abierto (nunca bytes vacios)."""
        ...

    def write(self, data: bytes) -> int:
        """Escribe bytes crudos. Retorna cantidad de bytes escritos."""
        ...

    @property
    def is_open(self) -> bool:
        ...
```

Contrato clave: `readline()` devuelve `None` (no `b""`) cuando expira el timeout
sin datos. Ambas implementaciones normalizan esto.

### `adapters/serial_transport.py` — Transport real (pyserial)

```python
from __future__ import annotations
import logging
from typing import Optional
import serial

logger = logging.getLogger(__name__)


class SerialTransport:
    def __init__(self, port: str, baudrate: int = 115200, timeout: float = 1.0):
        self._port = port
        self._baudrate = baudrate
        self._timeout = timeout
        self._ser: Optional[serial.Serial] = None

    def open(self) -> None:
        if self.is_open:
            return
        self._ser = serial.Serial(
            port=self._port,
            baudrate=self._baudrate,
            timeout=self._timeout,
            write_timeout=self._timeout,
        )
        logger.info("Puerto serial abierto: %s @ %d baud", self._port, self._baudrate)

    def close(self) -> None:
        if self._ser is not None:
            try:
                self._ser.close()
            except Exception:
                logger.exception("Error cerrando puerto serial %s", self._port)
            finally:
                self._ser = None
                logger.info("Puerto serial cerrado: %s", self._port)

    def readline(self) -> Optional[bytes]:
        if self._ser is None:
            return None
        try:
            line = self._ser.readline()
        except (serial.SerialException, OSError) as e:
            logger.error("Error leyendo puerto serial %s: %s", self._port, e)
            self.close()
            return None
        # pyserial devuelve b"" (no None) cuando expira el timeout sin datos;
        # lo traducimos a None para cumplir el contrato del Protocol Transport.
        return line if line else None

    def write(self, data: bytes) -> int:
        if self._ser is None:
            raise ConnectionError(f"Puerto serial {self._port} no esta abierto")
        try:
            return self._ser.write(data)
        except (serial.SerialException, OSError) as e:
            logger.error("Error escribiendo en puerto serial %s: %s", self._port, e)
            self.close()
            raise

    @property
    def is_open(self) -> bool:
        return self._ser is not None and self._ser.is_open
```

- Defaults: `baudrate=115200`, `timeout=1.0` (lectura y escritura).
- Un error de lectura o escritura llama `self.close()` (fuerza reconexion desde
  `SerialManager`). El error de escritura ademas **re-lanza** la excepcion; el de
  lectura devuelve `None`.

### `adapters/mock_transport.py` — simulador de hardware

Genera los 3 tipos de paquete de subida (frame fragmentado en chunks JPEG
reales, audio_sensors, env_and_actuation) con timing aproximado a un sistema
real, y responde a comandos de bajada con un `cmd_ack` simulado tras un delay —
como haria el firmware una vez lo implemente.

Constantes exactas:

```python
_CHUNK_SIZE = 512
_FRAME_INTERVAL_S = 1.0 / 10  # ~10 fps simulados
_AUDIO_INTERVAL_S = 0.5
_ENV_INTERVAL_S = 1.0
_ACK_DELAY_S = 0.3
```

Comportamiento:

- `__init__(seed=None)` — usa `random.Random(seed)` para trafico reproducible;
  `queue.Queue()` interna; contador `_frame_id` arranca en 0.
- `open()` — lanza un hilo daemon `MockTransportFeed` que corre `_feed_loop()`;
  idempotente si `_running`.
- `close()` — baja `_running`, hace `join(timeout=2.0)`.
- `readline()` — `self._queue.get(timeout=0.2)`, devuelve `None` en `queue.Empty`.
- `write(data)` — **simula la recepcion de un comando por No3**: parsea `data`
  como JSON; si falla (no-JSON), loguea warning y retorna `len(data)`. Si el
  comando trae `cmd_id`, agenda con `threading.Timer(_ACK_DELAY_S, self._emit_ack, ...)`
  un `cmd_ack` tras 0.3s (el `target_node` del comando pasa a ser el `node_id`
  del ack; default `"esp32_s3_no2"` si no viene). Retorna `len(data)`.
- `is_open` — devuelve `_running`.

Generacion de trafico (`_feed_loop`): loop `while self._running` con
`time.sleep(0.01)`, que emite cada tipo cuando `time.monotonic()` supera su
proximo hito:

- **frame** (`_emit_frame`): `_frame_id += 1`; genera un JPEG sintetico de
  120x160 con `cv2.imencode`, lo parte en chunks de `_CHUNK_SIZE=512` bytes,
  y emite un `FramePacket` por chunk con `seq`/`seq_total`, `node_id="esp32_s3_no1"`,
  `payload_b64` = base64 del chunk.
- **audio** (`_emit_audio`): `node_id="esp32_s3_no1"`, `mic1_db`/`mic2_db`
  aleatorios en `[35, 70]` redondeados a 1 decimal.
- **env** (`_emit_env`): `node_id="esp32_s3_no2"`; GPS alrededor de
  Arequipa (`-16.4090, -71.5375`) con jitter ±0.001, `sats` en `[4,12]`,
  `tof_distance_mm` en `[50,2000]`, polvo, dos lecturas de gas
  (`raw_adc` + `ppm_est`), `led_state="green_blink"`, motores en 0,
  `battery_v` en `[10.5, 12.6]`, `gyro=None`.

`_put(packet)` serializa el dict a `json.dumps(...) + "\n"` en UTF-8 y lo encola
(mismo formato de linea que el hardware real).

### `services/serial_manager.py` — hilo lector + escritura con lock + reconnect

Recibe cualquier `Transport`, parsea cada linea como `UplinkPacket` (validado con
Pydantic) y la entrega via callback. Escribe comandos de bajada de forma
thread-safe, protegidos por un lock para que escrituras concurrentes no se
entrelacen byte a byte en el mismo puerto.

```python
PacketCallback = Callable[[UplinkPacket], None]
LinkStatusCallback = Callable[[bool], None]

_RECONNECT_BACKOFF_INITIAL_S = 1.0
_RECONNECT_BACKOFF_MAX_S = 15.0
```

Firma:

```python
class SerialManager:
    def __init__(
        self,
        transport: Transport,
        on_packet: PacketCallback,
        on_link_status: Optional[LinkStatusCallback] = None,
    ):
```

Modelo de hilos:

- **Un hilo lector daemon** (`SerialManager`) que corre `_run()`: si el transport
  no esta abierto, marca link caido y hace `open()`. Si `open()` falla, hace
  backoff exponencial: `time.sleep(backoff)` empezando en 1.0s, duplicando hasta
  15.0s max (`backoff = min(backoff * 2, _RECONNECT_BACKOFF_MAX_S)`). Al abrir
  exitosamente, resetea `backoff` a 1.0s. Luego marca link arriba, hace
  `readline()`; si es `None` continua, si no llama `_handle_line(raw)`.
- **Escritura con lock** (`send_command`): serializa el `DownlinkCommand` con
  `model_dump_json()` + `b"\n"`, toma `self._write_lock`, verifica `is_open`
  (si no, warning y return), escribe. Cualquier excepcion de escritura se
  loguea con `logger.exception` pero **no se propaga** (el enlace se reintenta
  solo desde el hilo lector).

`_handle_line(raw)` — pipeline de parseo defensivo, descarta (con warning) y
continua en cada fallo:

1. `raw.decode("utf-8").strip()` → `UnicodeDecodeError` descarta.
2. Linea vacia → return silencioso.
3. `json.loads(text)` → `JSONDecodeError` descarta.
4. `uplink_adapter.validate_python(payload)` → `ValidationError` descarta
   (loguea el `packet_type` ofensor).
5. `self._on_packet(packet)` envuelto en try/except: si el callback falla, se
   loguea con `logger.exception` pero el hilo lector sigue vivo.

`_set_link_status(up)` — **edge-triggered**: solo loguea y llama
`on_link_status` cuando el estado cambia (`up != self._link_up`), no en cada
iteracion.

`__main__` — demo que cuenta chunks por frame usando `MockTransport(seed=42)` y
envia un comando `set_leds` tras 2s.

## Fase 2 — Reensamblado de frames

### `services/frame_reassembler.py`

Reconstruye frames JPEG completos a partir de fragmentos `FramePacket`
(`seq`/`seq_total`) que llegan potencialmente fuera de orden o incompletos por
perdida de paquetes en el trayecto ESP-NOW -> USB serial. Frames que no completan
todos sus chunks dentro de `timeout_s` se descartan (nunca se entregan a
deteccion) y quedan logueados.

```python
# frame_id, jpeg_bytes, timestamp_ms del primer chunk
FrameCompleteCallback = Callable[[int, bytes, int], None]

_DEFAULT_TIMEOUT_S = 2.0
_DEFAULT_PRUNE_INTERVAL_S = 0.5
```

Estructura interna:

```python
@dataclass
class _PendingFrame:
    seq_total: int
    node_id: str
    timestamp_ms: int
    chunks: dict = field(default_factory=dict)  # seq -> bytes
    first_seen: float = field(default_factory=time.monotonic)

    def is_complete(self) -> bool:
        return len(self.chunks) == self.seq_total

    def assemble(self) -> bytes:
        return b"".join(self.chunks[i] for i in range(self.seq_total))
```

Firma:

```python
class FrameReassembler:
    def __init__(
        self,
        on_frame_complete: FrameCompleteCallback,
        timeout_s: float = _DEFAULT_TIMEOUT_S,
        prune_interval_s: float = _DEFAULT_PRUNE_INTERVAL_S,
    ):
```

Algoritmo de `add_chunk(packet)`:

1. **Validacion de bounds**: descarta si `seq_total <= 0` o
   `not (0 <= seq < seq_total)`.
2. **Decodifica base64** con `validate=True`; si falla, descarta con warning.
3. Bajo `self._lock`:
   - Busca el `_PendingFrame` de `frame_id`. Si no existe, o si su `seq_total`
     cambio respecto al del paquete (frame_id reusado con distinto tamaño),
     crea uno nuevo (loguea warning en el caso de cambio de `seq_total` a mitad).
   - Si `seq` ya estaba en `chunks`, ignora duplicado (`logger.debug`). Si no,
     lo guarda.
   - Si `is_complete()`, marca `complete_frame` y hace `del self._pending[frame_id]`.
4. Fuera del lock, si se completo, llama `_deliver()`.

`_deliver()` ensambla con `assemble()` (concatena chunks en orden 0..seq_total-1)
y llama `on_frame_complete(frame_id, jpeg_bytes, timestamp_ms)`; ambas
operaciones envueltas en try/except con `logger.exception`.

Poda por timeout (`start()` lanza hilo daemon `FrameReassemblerPrune` que corre
`_prune_loop`): cada `prune_interval_s=0.5s`, `_prune_stale()` toma el lock,
recolecta los `frame_id` cuyo `now - first_seen > timeout_s`, los saca del dict, y
fuera del lock loguea por cada uno cuantos chunks se recibieron. Esto garantiza
que un frame incompleto se limpie **sin depender** de que sigan llegando chunks
nuevos.

`__main__` — inyecta a proposito un frame incompleto (`frame_id=99999`, 1 de 3
chunks) para verificar que `_prune_stale()` lo descarta tras el timeout.

## Fase 3 — Pipeline de deteccion

### `services/detection_service.py`

Corre el pipeline completo (caidas + EPP + entorno/escombros + fusion) sobre
frames JPEG ya reensamblados. **Reusa exactamente**:

- `detectors/fall_detector.py` → `FallDetector`
- `detectors/epp_detector.py` → `EppDetector`, `CONF_EPP_DEFAULT` (0.30),
  `CONF_VICTIM_DEFAULT` (0.25)
- `detectors/rescue_detector.py` → `RescueDetector`, `CONF_ENV_DEFAULT` (0.35)
- `ukucha_detector.py` (raiz) → funciones de fusion `classify_rubble_victims`,
  `draw_blocked_access`, `link_victims_access`, `pick_device`

**Por que reusar y no reimplementar** (decision de arquitectura critica): este
proyecto ya sufrio una vez el problema de divergencia entre `fall_detector.py` y
`webcam_fall.py` (dos copias de la misma logica que se desincronizaron).
`DetectionService` importa las funciones de fusion directamente desde
`ukucha_detector.py` para que exista **una sola fuente de verdad**: si mañana se
ajusta la logica de fusion, la webcam y el backend cambian juntos, no se vuelven
a desincronizar. Nada se reimplementa aca, solo se orquesta sobre una fuente de
frames distinta (JPEG reensamblado desde serial en vez de `WebcamStream`).

```python
_JPEG_QUALITY = 85
```

Firma completa:

```python
class DetectionService:
    def __init__(
        self,
        device: Optional[object] = None,
        env_every: int = 5,
        conf_victim: float = CONF_VICTIM_DEFAULT,
        conf_epp: float = CONF_EPP_DEFAULT,
        conf_env: float = CONF_ENV_DEFAULT,
        route_frac: float = 0.35,
        enable_fall: bool = True,
        enable_epp: bool = True,
        enable_rescue: bool = True,
        show_all_epp: bool = False,
    ):
```

Construccion:

- `device` = argumento o `pick_device()` (auto: `0` para cuda:0, o `"cpu"`).
- `_check_models(...)` (staticmethod) valida que existan los `.pt` requeridos en
  `<raiz>/models/` (subiendo 2 niveles desde `backend/services/` con
  `Path(__file__).resolve().parents[2] / "models"`): `yolov8n.pt` (fall),
  `epp_yolo8m.pt` (EPP), `drespnet_best.pt` (rescue). Lanza `FileNotFoundError`
  con la ruta esperada si falta alguno.
- `env_every = max(1, env_every)` — RescueDetector corre 1 de cada N frames.
- Instancia los 3 detectores (o `None` si estan deshabilitados).
- Estado: `_frame_idx = 0`, `_last_env_result = None`.

`process_jpeg(frame_id, jpeg_bytes, timestamp_ms) -> Optional[dict]`:

1. `cv2.imdecode(...)`; si `None`, warning y return `None`.
2. `_frame_idx += 1`; calcula `diag = hypot(w, h)`.
3. `infer_frame = frame.copy()` — `infer_frame` se pasa a los detectores para
   inferencia, `frame` es el **canvas** que acumula anotaciones de las 3 capas
   (mismo patron que `ukucha_detector.py`).
4. **Caidas**: `fall_detector.process(infer_frame, now, mostrar_landmarks=True, device, canvas=frame)`.
   Default `{"hay_alerta": False, "hay_critica": False, "personas": []}`.
5. **Entorno/rescate** (throttled por `env_every`): recomputa si
   `env_every <= 1` o `_frame_idx % env_every == 0` o `_last_env_result is None`.
   Al recomputar hace `rescue_detector.process(...)` y pinta con `.plot(img=frame)`.
   Siempre extrae del ultimo resultado (aunque no recompute):
   `extract_access`, `extract_hazards` (que devuelve `hazards`, `civilians`,
   `rescue_teams`, `blocked`), y `count_detections` → `n_env`.
6. **EPP**: `epp_detector.process(infer_frame, conf_victim, conf_epp, show_all_epp, canvas=frame)`
   → `victims`, `n_rescuer`, `n_epp`, `bodyparts`.
7. **Rutas**: si hay `victims` y `accesses`, `n_routes = link_victims_access(frame, victims, accesses, route_frac * diag)`.
8. **Fusion**: si hay `hazards` o `civilians`,
   `fusion = classify_rubble_victims(frame, bodyparts, hazards, civilians, victims, fall_result["personas"])`.
9. Si hay `blocked`, `draw_blocked_access(frame, blocked)`.
10. Re-codifica el canvas anotado con `cv2.imencode(".jpg", frame, [IMWRITE_JPEG_QUALITY, 85])`;
    si falla, reenvia el JPEG original.
11. Devuelve el dict crudo (la clave para `output_builder`):

```python
{
    "frame_id": frame_id,
    "timestamp_ms": timestamp_ms,
    "annotated_jpeg": annotated_jpeg,
    "fall": fall_result,  # {hay_alerta, hay_critica, personas:[{estado, score, bbox}]}
    "epp": {"victims", "n_rescuer", "n_epp", "bodyparts"},
    "env": {"accesses", "hazards", "civilians", "rescue_teams", "blocked", "n_env"},
    "fusion": {**fusion, "n_routes"},  # fusion: rubble_victims, n_fall_rubble, n_risk_zones, n_civilians
}
```

`close()` cierra el `fall_detector` (MediaPipe requiere cierre explicito).

**Hallazgo de Fase 3 — warm-up de CUDA (~5s primer frame)**: el primer
`process_jpeg` sufre el JIT/compilacion de kernels CUDA de PyTorch y tarda ~5s;
los siguientes son de decenas de ms. Por eso `app.py` corre un frame dummy al
arrancar (ver `_warmup`) para absorber ese pico antes del primer frame real.

## Fase 4 — WebSocket + comandos

### `services/detection_worker.py`

**Por que existe**: la inferencia (decenas de ms en estado estable, con el pico
de ~5s en el primer frame por CUDA JIT) **nunca debe bloquear el hilo lector
serial**. `DetectionWorker` corre `DetectionService.process_jpeg` en un hilo
daemon dedicado.

```python
ResultCallback = Callable[[dict], None]
_DEFAULT_QUEUE_MAXSIZE = 2
```

- `submit_frame(frame_id, jpeg_bytes, timestamp_ms)` — pensado para usarse como
  `on_frame_complete` de `FrameReassembler` (se llama desde el hilo lector).
  Encola con `put_nowait`; si la cola esta llena (`queue.Full`), **descarta el
  frame** con warning ("deteccion no da abasto") en vez de acumular latencia
  creciente. Mismo criterio que `WebcamStream`: siempre trabajar con el dato mas
  reciente posible.
- `_run()` — loop daemon: `get(timeout=0.2)`, corre `process_jpeg` (envuelto en
  try/except), y si el resultado no es `None`, llama `on_result` (tambien
  protegido).

### `services/telemetry_store.py`

Guarda el ultimo estado conocido de `audio_sensors` y `env_and_actuation`,
marcando `stale=True` si no llegan datos frescos dentro de `stale_after_s`
(posible falla del enlace ESP-NOW hacia No1/No2). Thread-safe (`threading.Lock`):
se escribe desde el hilo lector serial y se lee desde el loop de broadcast.

```python
_DEFAULT_STALE_AFTER_S = 5.0
```

API:

- `update_audio(packet: AudioSensorsPacket)` / `update_env(packet: EnvActuationPacket)`
  — guardan el packet y el `time.monotonic()` de recepcion, bajo lock.
- `get_audio() -> dict` — si nunca se recibio nada:
  `{"mic1_db": None, "mic2_db": None, "stale": True}`. Si hay dato:
  `stale = (now - received_at) > stale_after_s`.
- `get_env() -> dict` — si nunca se recibio: todos los campos `None` +
  `"stale": True` + `"motors": None`. Si hay dato: expone `gps`,
  `tof_distance_mm`, `dust_pms5003`, `gas_mq7_co`, `gas_mq136_h2s`, `led_state`,
  `battery_v`, `stale`, y `motors`. **Nota**: `motors` viaja dentro del dict de
  `get_env()` y luego `output_builder` lo saca (`env.pop("motors")`) para
  ubicarlo como campo top-level de la salida.

### `services/command_service.py`

Valida comandos entrantes del panel, determina el `target_node` correcto por
tipo de comando (el panel no necesita conocer la topologia de hardware), asigna
un `cmd_id` incremental, y trackea si llega confirmacion dentro de un timeout.

```python
_ACK_TIMEOUT_S = 3.0

class SetMotorsParams(BaseModel):
    m1: int; m2: int; m3: int; m4: int
class SetLedsParams(BaseModel):
    pattern: str
class CameraRestartParams(BaseModel):
    pass  # sin parametros

_COMMAND_TARGET_NODE = {
    "set_motors":     "esp32_s3_no2",
    "set_leds":       "esp32_s3_no2",
    "camera_restart": "esp32_s3_no1",
}
_COMMAND_PARAM_SCHEMA = {
    "set_motors":     SetMotorsParams,
    "set_leds":       SetLedsParams,
    "camera_restart": CameraRestartParams,
}
```

Tabla de auto-asignacion de `target_node`:

| command | target_node | params schema |
|---|---|---|
| `set_motors` | `esp32_s3_no2` | `{m1,m2,m3,m4}` (int) |
| `set_leds` | `esp32_s3_no2` | `{pattern}` (str) |
| `camera_restart` | `esp32_s3_no1` | `{}` (vacio) |

Firma:

```python
class CommandService:
    def __init__(self, send_fn: SendFn, ack_timeout_s: float = _ACK_TIMEOUT_S,
                 on_log: Optional[LogFn] = None):
```

- `dispatch(command, params) -> DownlinkCommand`: busca `target_node` y schema;
  si el comando es desconocido lanza `ValueError`. Valida params contra el schema
  (`ValidationError` → `ValueError`). Asigna `cmd_id` con
  `itertools.count(1)` (arranca en 1). Construye el `DownlinkCommand`, registra
  el pendiente (arma `threading.Timer(ack_timeout_s, _on_timeout)`), llama
  `send_fn(cmd)`, y loguea el evento `"sent"` via `_log`.
- `on_ack(cmd_id, status)`: bajo lock saca el pendiente; si existe, cancela su
  timer, loguea `"ack"`. Si no existe (timeout previo o duplicado), warning.
- `_on_timeout(cmd_id)`: bajo lock saca el pendiente; si sigue ahi, loguea
  `"SIN CONFIRMACION ... posible falla ESP-NOW"` y evento `"timeout"`.
- **`on_log` hook**: callback opcional `LogFn = Callable[[dict], None]` que
  recibe un registro de auditoria en cada transicion (`sent`/`ack`/`timeout`).
  En Fase 5 se cablea a `persistence_worker.save_command_log` para persistir el
  ciclo de vida de cada comando. El registro incluye `cmd_id`, `command`,
  `target_node`, `params` (solo en `sent`), `event`, `status`, `ts`. Cualquier
  excepcion del hook se traga con `logger.exception` (nunca rompe el dispatch).

### `schemas/output.py` — EnrichedFrameOutput (DECISION DE DISEÑO)

**Esquema EXTENDIDO, no aplanado.** El ejemplo generico del prompt original
proponia aplanar todo a una lista de `{class, confidence, bbox}`. Este sistema
**preserva la riqueza de la fusion de 6 escenarios** que ya produce el pipeline
(fall / epp / fusion) en campos anidados tipados. El array `detections` se
mantiene como **subconjunto plano derivado** — compatibilidad con integraciones
simples del panel — pero **NO es la fuente de verdad**: los conteos ricos viven
en los campos anidados (`fall`, `epp`, `fusion`). Aplanar seria perder informacion
(no distingue victima confirmada de indicio, ni caida critica de alerta, ni
cuenta rutas/zonas de riesgo).

```python
class Detection(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    class_: str = Field(alias="class")   # "class" es palabra reservada -> alias
    confidence: Optional[float] = None   # None cuando la deteccion origen no trae confianza
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
    mic1_db: Optional[float] = None
    mic2_db: Optional[float] = None
    stale: bool

class EnvState(BaseModel):
    gps: Optional[GpsData] = None
    tof_distance_mm: Optional[int] = None
    dust_pms5003: Optional[DustData] = None
    gas_mq7_co: Optional[GasReading] = None
    gas_mq136_h2s: Optional[GasReading] = None
    led_state: Optional[str] = None
    battery_v: Optional[float] = None
    stale: bool

class EnrichedFrameOutput(BaseModel):
    frame_id: int
    timestamp: str        # ISO 8601 UTC
    image_b64: str        # data:image/jpeg;base64,...
    detections: List[Detection]
    fall: FallInfo
    epp: EppInfo
    fusion: FusionInfo
    audio: AudioState
    env: EnvState
    motors: Optional[MotorsState] = None
```

`GpsData`, `DustData`, `GasReading`, `MotorsState` se **reimportan** desde
`schemas/uplink.py` (una sola definicion). El campo `Detection.class_` usa
`alias="class"` + `populate_by_name=True`, por eso el broadcast usa
`model_dump_json(by_alias=True)` para que en el JSON salga `"class"`.

### `services/output_builder.py`

Unico lugar donde se aplana la fusion rica al array `detections`. Firma:
`build_enriched_output(result: dict, telemetry_store: TelemetryStore) -> EnrichedFrameOutput`.

Derivacion del array plano `detections` (clases en español, para el panel):

| Fuente en `result` | Condicion | `class` | `confidence` |
|---|---|---|---|
| `fall.personas` | `estado in ("EN EL SUELO", "CAYENDO")` | `persona_caida` | `persona["score"]` |
| `epp.victims` (tuplas `tid, bbox, confirmable`) | `confirmable` | `victima` | `None` |
| `epp.victims` | `not confirmable` | `indicio_persona` | `None` |
| `env.hazards` | siempre | `escombro` | `hconf` |
| `env.civilians` | siempre | `civil` | `cconf` |
| `env.blocked` | siempre | `acceso_bloqueado` | `bconf` |
| `env.rescue_teams` | siempre | `equipo_rescate` | `rconf` |

Luego: lee `telemetry_store.get_audio()` y `get_env()`; saca `motors` de env con
`env.pop("motors", None)`; arma `image_b64 = "data:image/jpeg;base64," + b64(annotated_jpeg)`;
`timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")`. Los
conteos ricos se calculan aca (`n_personas=len(personas)`,
`n_victims=len(victims)`, `n_rubble_victims=len(rubble_victims)`, etc).

### `api/deps.py`

```python
def get_command_service(request: Request) -> CommandService:
    return request.app.state.command_service
```

Los WebSocket leen `websocket.app.state.command_service` directo (patron
equivalente sin `Depends`, porque `Depends` con `Request` no aplica a WS).

### `api/ws_stream.py` — WebSocket `/ws/stream` (salida)

Solo gestiona el ciclo de vida de la conexion: en `accept()` agrega el socket a
`app.state.stream_clients` (un `set`), loguea, y hace `receive_text()` en loop
solo para detectar la desconexion (no espera contenido del panel). En
`WebSocketDisconnect`/`finally` hace `clients.discard(websocket)`. El broadcast
real (envio de `EnrichedFrameOutput`) ocurre en `_broadcast_loop` de `app.py`.

### `api/ws_commands.py` — `/ws/commands` + `POST /api/commands` (entrada)

```python
class IncomingCommandRequest(BaseModel):
    command: str
    params: dict = Field(default_factory=dict)
```

- **`WS /ws/commands`**: loop `receive_json()` → valida con
  `IncomingCommandRequest` → `command_service.dispatch(command, params)`. En
  `ValidationError`/`ValueError` responde `{"ok": False, "error": str(e)}` y
  continua. En exito responde `{"ok": True, "cmd_id": ..., "command": ...}`.
- **`POST /api/commands`**: mismo cuerpo, via `Depends(get_command_service)`;
  en `ValueError` responde `{"ok": False, "error": ...}`, en exito
  `{"ok": True, "cmd_id": ..., "command": ...}`. (No captura `ValidationError`
  aparte porque FastAPI ya valida el body antes de entrar.)

### `app.py` — ensamblado

`create_app()` cablea todo y devuelve el `FastAPI`. `app = create_app()` corre a
**nivel de modulo** (necesario para que `uvicorn backend.app:app` encuentre el
objeto ASGI). Esto carga los 3 modelos YOLO + MediaPipe + warm-up de CUDA como
efecto secundario de importar el archivo.

Variables de entorno (leidas al importar, tras `load_dotenv()`):

| Variable | Default | Uso |
|---|---|---|
| `UKUCHA_USE_MOCK` | `1` (mock) | `!= "0"` usa `MockTransport`; `"0"` usa `SerialTransport` |
| `UKUCHA_SERIAL_PORT` | `COM3` | puerto real (ignorado en modo mock) |
| `UKUCHA_BAUDRATE` | `115200` | baudrate del puerto real |
| `UKUCHA_ENV_EVERY` | `5` | RescueDetector 1 de cada N frames |
| `SUPABASE_URL` | (vacio) | si falta, `NullPersistenceAdapter` |
| `SUPABASE_KEY` | (vacio) | si falta, `NullPersistenceAdapter` |

Cableado en `create_app()`:

1. `telemetry_store = TelemetryStore()`.
2. `detection_service = DetectionService(env_every=ENV_EVERY)` y `_warmup(...)`.
3. `_build_persistence_backend()` → `SupabaseAdapter` si hay credenciales (import
   perezoso, con fallback a `NullPersistenceAdapter` si falla la init), si no
   `NullPersistenceAdapter`. Envuelto en `PersistenceWorker`.
4. `event_detector = EventDetector()`.
5. `_on_detection_result(result)` callback: `build_enriched_output` →
   por cada evento de `event_detector.detect(output)` llama
   `persistence_worker.save_event` → encola la salida en `app.state.output_queue`
   via `loop.call_soon_threadsafe(_safe_put, ...)` (cruce de hilo daemon a event
   loop asyncio).
6. `detection_worker = DetectionWorker(detection_service, on_result=_on_detection_result)`.
7. `reassembler = FrameReassembler(on_frame_complete=detection_worker.submit_frame)`.
8. `command_service = CommandService(send_fn=lambda cmd: serial_manager.send_command(cmd), on_log=persistence_worker.save_command_log)`.
   El lambda referencia `serial_manager`, que se define despues — valido porque
   solo se ejecuta cuando el panel dispare un comando (post-arranque).
9. `_on_packet(packet)` router por tipo: `FramePacket` → `reassembler.add_chunk`;
   `AudioSensorsPacket` → `telemetry_store.update_audio` + `save_telemetry`;
   `EnvActuationPacket` → `telemetry_store.update_env` + `save_telemetry`;
   `CmdAckPacket` → `command_service.on_ack`.
10. `transport = MockTransport() if USE_MOCK else SerialTransport(...)`;
    `serial_manager = SerialManager(transport, on_packet=_on_packet)`.

**Lifespan** (`@asynccontextmanager`) — orden de arranque:

1. `app.state.loop = asyncio.get_running_loop()`.
2. `persistence_worker.start()`
3. `reassembler.start()`
4. `detection_worker.start()`
5. `serial_manager.start()`
6. `broadcast_task = asyncio.create_task(_broadcast_loop(app))`

Orden de apagado (en `finally`, inverso-ish):
`broadcast_task.cancel()` → `serial_manager.stop()` → `detection_worker.stop()`
→ `reassembler.stop()` → `persistence_worker.stop()` → `detection_service.close()`.

**CORS** — configurado (agregado tras el code review): `allow_origins=["*"]`,
`allow_methods=["*"]`, `allow_headers=["*"]` (sin `allow_credentials`, mismo
criterio que `server.py`).

`app.state`: `stream_clients = set()`, `output_queue = asyncio.Queue(maxsize=4)`,
`command_service`.

`_broadcast_loop(app)`: consume `output_queue`, serializa con
`model_dump_json(by_alias=True)`, y hace `send_text` a cada cliente de
`stream_clients` (descarta el que falle). `_safe_put` descarta con warning si la
cola esta llena (`asyncio.QueueFull`).

App: `FastAPI(title="UKUCHA Backend v2", version="0.2.0", lifespan=lifespan)`;
incluye `stream_router` y `commands_router`.

## Fase 5 — Persistencia no bloqueante

### `ports/persistence.py` — Protocol PersistenceBackend

```python
class PersistenceBackend(Protocol):
    def save_event(self, event: dict) -> None: ...
    def save_telemetry(self, record: dict) -> None: ...
    def save_command_log(self, record: dict) -> None: ...
```

### `adapters/null_adapter.py` — default sin credenciales

`NullPersistenceAdapter` implementa los 3 metodos solo logueando (`logger.info`
con prefijo `[persistencia-null]`). Es el adapter **por defecto** cuando faltan
`SUPABASE_URL`/`SUPABASE_KEY`: permite desarrollar y probar todos los hooks de
persistencia sin un proyecto Supabase real. El resto del backend funciona identico.

### `adapters/supabase_adapter.py`

```python
TABLE_EVENTS = "detection_events"
TABLE_TELEMETRY = "telemetry_history"
TABLE_COMMANDS = "command_log"

class SupabaseAdapter:
    def __init__(self, url: str, key: str):
        from supabase import Client, create_client  # import perezoso
        self._client = create_client(url, key)
    def save_event(self, event): self._insert(TABLE_EVENTS, event)
    def save_telemetry(self, record): self._insert(TABLE_TELEMETRY, record)
    def save_command_log(self, record): self._insert(TABLE_COMMANDS, record)
    def _insert(self, table, record):
        self._client.table(table).insert(record).execute()
```

El import de `supabase` es **perezoso** (dentro de `__init__`) para que el resto
del backend no dependa del paquete si no se usa Supabase. Cada metodo hace un
insert simple; los errores se **propagan** al llamador (`PersistenceWorker`), que
los captura y silencia — este adapter NO maneja reintentos ni backpressure.

### `services/persistence_worker.py`

Escribe al backend configurado en un **hilo daemon aparte con cola acotada**,
para que nunca bloquee el pipeline de tiempo real. **Mismo patron que
`ServerNotifier` en `ukucha_detector.py`** (patron probado reusado): si el
backend esta caido, lento, o no configurado, los registros se descartan — nunca
se traba ni propaga excepcion.

```python
_QUEUE_MAXSIZE = 200
```

- `save_event` / `save_telemetry` / `save_command_log` → `_enqueue(kind, record)`
  con `put_nowait`; en `queue.Full` hace `pass` (descarta, no acumula lag).
- `_run()` — loop daemon: `get(timeout=0.2)`, despacha al backend segun `kind`
  (`event`/`telemetry`/`command`). Ante cualquier excepcion loguea **una sola
  vez por tipo** (`self._warned[kind]`) y silencia los avisos futuros de ese tipo
  (evita spamear el log si Supabase esta caido).

### `services/event_detector.py`

Decide que salidas del pipeline son "eventos relevantes" para persistir, usando
la misma **logica de borde de subida (transicion False->True)** que
`ServerNotifier` ya usa en `ukucha_detector.py` (patron de notificacion basada
en transiciones reusado). Evita escribir el mismo evento en cada frame mientras
la alerta se mantiene activa, y evita perder la coordenada GPS del momento.

Estado: `_prev_alerta`, `_prev_critica`, `_prev_rubble` (arrancan `False`).

`detect(output: EnrichedFrameOutput) -> List[dict]`:

- Extrae `gps = output.env.gps.model_dump() if not None else None`.
- **Caida** (prioridad critica > alerta, con `elif`):
  - `hay_critica and not _prev_critica` → evento `caida_critica`
    (con `detalle="persona en el suelo por tiempo prolongado"`).
  - `elif hay_alerta and not _prev_alerta` → evento `caida_detectada`.
  - Actualiza `_prev_alerta`, `_prev_critica`.
- **Escombros**: `rubble_now = n_rubble_victims > 0`; si `rubble_now and not
  _prev_rubble` → evento `persona_bajo_escombros`
  (con `detalle="{n} victima(s)"`). Actualiza `_prev_rubble`.
- Cada evento lleva `tipo`, `frame_id`, `timestamp`, `gps` (+ `detalle` cuando
  aplica).

### `supabase_schema.sql` — 3 tablas

Ejecutar en el SQL Editor de Supabase antes de configurar las credenciales.

| Tabla | Proposito | Columnas clave |
|---|---|---|
| `detection_events` | eventos de deteccion (transiciones de alerta) con GPS | `tipo`, `frame_id`, `detalle`, `gps jsonb`, `event_timestamp timestamptz` |
| `telemetry_history` | historico de cada paquete audio/env | `kind`, `node_id`, `timestamp_ms bigint`, `data jsonb` |
| `command_log` | auditoria de comandos enviados | `cmd_id`, `command`, `target_node`, `params jsonb`, `event` (sent/ack/timeout), `status` |

Indices: `idx_telemetry_history_kind_ts (kind, timestamp_ms)`,
`idx_command_log_cmd_id (cmd_id)`,
`idx_detection_events_tipo_ts (tipo, event_timestamp)`. Todas usan
`id bigint generated always as identity primary key` y `created_at timestamptz default now()`.

## API completa (superficie WebSocket + REST)

| Metodo | Ruta | Entrada | Salida |
|---|---|---|---|
| WS | `/ws/stream` | (nada; solo detecta desconexion) | broadcast de `EnrichedFrameOutput` (JSON, `by_alias`) |
| WS | `/ws/commands` | `{"command": str, "params": dict}` | `{"ok": true, "cmd_id": int, "command": str}` o `{"ok": false, "error": str}` |
| POST | `/api/commands` | `{"command": str, "params": dict}` | `{"ok": true, "cmd_id": int, "command": str}` o `{"ok": false, "error": str}` |

No hay endpoint REST de GET para historicos en este backend v2 (a diferencia de
`server.py`): el panel consume el stream en vivo por `/ws/stream` y el historico
vive en Supabase.

## Dependencias nuevas (requirements.txt)

Versiones pinneadas exactas agregadas para este backend:

| Paquete | Version | Rol |
|---|---|---|
| `pyserial` | `3.5` | `SerialTransport` (enlace USB real) |
| `supabase` | `2.31.0` | `SupabaseAdapter` |
| `httpx2` | `2.7.0` | transitiva de supabase (cliente HTTP) |
| `httpcore2` | `2.7.0` | transitiva (nucleo HTTP de httpx2) |
| `truststore` | `0.10.4` | verificacion TLS con el store de certificados del SO |
| `postgrest` | `2.31.0` | transitiva de supabase (API REST de Postgres) |
| `realtime` | `2.31.0` | transitiva de supabase |
| `storage3` | `2.31.0` | transitiva de supabase |
| `supabase-auth` | `2.31.0` | transitiva de supabase |
| `supabase-functions` | `2.31.0` | transitiva de supabase |
| `StrEnum` | `0.4.15` | transitiva de supabase |
| `deprecation` | `2.1.0` | transitiva |
| `h2` / `hpack` / `hyperframe` | `4.3.0` / `4.2.0` / `6.1.0` | HTTP/2 (transitivas) |

`fastapi==0.139.2`, `uvicorn==0.51.0`, `starlette==1.3.1`, `websockets==15.0.1`,
`pydantic==2.13.4`, `python-dotenv==1.2.2` ya estaban o soportan el backend.

## Gaps y decisiones conocidas del code review (citar honestamente)

1. **No hay `opencv-python` en requirements.txt — es INTENCIONAL.** `ultralytics`
   declara `opencv-python` como dependencia en su metadata, asi que `pip check`
   lo marca como "missing" — es esperado. **NO agregar `opencv-python` de vuelta.**
   Instalar `opencv-python` y `opencv-contrib-python` a la vez pisa el modulo
   `cv2` entre si (mismo import path, versiones distintas) y fue la causa raiz
   corregida en **commit 756e08b**. `opencv-contrib-python==4.11.0.86` es superset
   y ya provee `cv2` para todo el proyecto (`detectors/`, `backend/`, mediapipe).
2. **Los modelos se cargan a la hora de importar la app** (`app = create_app()`
   a nivel de modulo). Esto duplica los 3 modelos en VRAM por worker, asi que el
   backend es **single-worker only**: NO usar `uvicorn --workers N>1`. Una GPU,
   un proceso.
3. **CORS ahora configurado** (agregado tras el review): antes faltaba y el panel
   en otro puerto no conectaba. Ahora abierto (`*`).
4. **`CmdAckPacket` no esta confirmado en el firmware** todavia — el backend ya
   lo parsea, el tracking de ack/timeout de `CommandService` funciona con el mock,
   pero contra hardware real el ack puede no llegar nunca hasta que el firmware
   lo emita (por eso el timeout solo loguea, no rompe nada).
5. **`GasReading.ppm_est` puede ser `None`** de forma persistente hasta que exista
   curva de calibracion Rs/Ro; el panel debe tolerar `null` en gases.

## Como ejecutar

### Modo mock (default, sin hardware)

```bash
venv\Scripts\python.exe -m uvicorn backend.app:app --host 0.0.0.0 --port 8000
```

Sin ninguna variable de entorno: `MockTransport` + `NullPersistenceAdapter`. El
backend genera trafico sintetico y corre el pipeline completo. Ideal para
desarrollar el panel sin placas.

### Modo hardware real

Copiar `env.example` a `.env` y setear:

```
UKUCHA_USE_MOCK=0
UKUCHA_SERIAL_PORT=COM3        # el puerto donde aparece el ESP32-S3 No3
UKUCHA_BAUDRATE=115200
```

(Opcional) para persistir en Supabase, ejecutar `backend/supabase_schema.sql` en
el proyecto y setear `SUPABASE_URL` / `SUPABASE_KEY`.

### Smoke test integrado (`app.py::__main__`)

```bash
venv\Scripts\python.exe -m backend.app
```

Usa `starlette.testclient.TestClient` (no requiere uvicorn) para:

1. Conectar `/ws/stream` y `/ws/commands`.
2. Enviar `{"command": "set_leds", "params": {"pattern": "red_solid"}}` y esperar
   el ack `{"ok": true, "cmd_id": ...}`.
3. Recibir 3 frames enriquecidos por `/ws/stream` (deadline 10s) y loguear
   `detections`, `fall.hay_alerta`, `audio.stale`, `env.stale`.
4. **Verificacion directa de `EventDetector`** (Fase 5): como el mock no genera
   personas/escombros reales, se prueba la logica de borde a mano — construye un
   `EnrichedFrameOutput` con `hay_alerta=True`, corre `detect()` dos veces, y
   asegura: primera vez 1 evento `caida_detectada`, segunda vez 0 eventos (no se
   repite sin nueva transicion).

## Verificacion

Estos son los pasos que se probaron efectivamente a lo largo de las 5 fases:

1. **Fase 1** — `python -m backend.services.serial_manager` → arranca
   `MockTransport(seed=42)`, cuenta chunks por frame, envia un `set_leds`, y a los
   ~0.3s recibe el `cmd_ack` simulado (log "Paquete recibido").
2. **Fase 2** — `python -m backend.services.frame_reassembler` → frames se
   reensamblan y decodifican como JPEG valido; el frame incompleto `99999`
   (1 de 3 chunks) se descarta por timeout con log "descartado por timeout".
3. **Fase 3** — `python -m backend.services.detection_service` → primer frame
   ~5s (warm-up CUDA), siguientes decenas de ms; log de latencia promedio y
   `jpeg_anotado_valido=True`. Confirma que las funciones de fusion importadas de
   `ukucha_detector.py` corren sin reimplementar nada.
4. **Fase 4** — `python -m backend.app` (bloque `__main__`) → 3 frames recibidos
   por `/ws/stream`, ack de comando por `/ws/commands`.
5. **Fase 5** — mismo `__main__` → assert de edge-detection de `EventDetector`
   pasa (1 evento en la transicion, 0 al repetir). Con `NullPersistenceAdapter`,
   los logs `[persistencia-null]` muestran lo que se hubiera guardado.
6. Levantar con uvicorn en modo mock → un cliente WS a `/ws/stream` recibe
   `EnrichedFrameOutput` con `image_b64` (data URI), `detections` (posiblemente
   vacio con ruido sintetico), `audio.stale`/`env.stale` que pasan de `True` a
   `False` cuando llegan los primeros paquetes de telemetria.
7. `POST /api/commands` con `{"command": "camera_restart", "params": {}}` →
   `{"ok": true, "cmd_id": N, "command": "camera_restart"}`, target auto-asignado
   a `esp32_s3_no1`.
8. `POST /api/commands` con un comando desconocido → `{"ok": false, "error": "Comando desconocido: ..."}`.
9. `POST /api/commands` con `set_motors` y params invalidos (falta `m3`) →
   `{"ok": false, "error": "Parametros invalidos ..."}`.

## Referencias

- `ukucha/sistema.md` — orquestador `ukucha_detector.py` (fuente de las funciones
  de fusion reusadas: `classify_rubble_victims`, `link_victims_access`,
  `draw_blocked_access`, `pick_device`, y del patron `ServerNotifier`).
- `ukucha/fall-detector.md` — `detectors/fall_detector.py` (`FallDetector`).
- `ukucha/epp-detector.md` — `detectors/epp_detector.py` (`EppDetector`,
  `CONF_EPP_DEFAULT`, `CONF_VICTIM_DEFAULT`).
- `ukucha/rescue-detector.md` — `detectors/rescue_detector.py` (`RescueDetector`,
  `CONF_ENV_DEFAULT`).
- `ukucha/server.md` — el servidor de telemetria v1 (`server.py`) que este
  backend v2 reemplaza para el flujo de hardware.
- Codigo: todo `backend/`, `backend/supabase_schema.sql`, `env.example`,
  `requirements.txt` (deps nuevas).
