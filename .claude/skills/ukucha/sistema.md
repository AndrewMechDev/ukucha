# Skill: UKUCHA — Sistema Integral de Seguridad Minera/SAR

## Objetivo

Sistema de seguridad para mineria y busqueda/rescate (SAR) que detecta caidas,
EPPs faltantes, personas atrapadas bajo escombros, y zonas de riesgo. Combina
3 modelos de vision por computadora con fusion cruzada para clasificar 6
escenarios de emergencia en tiempo real.

Proyecto para FLIT Hackathon 2026.

## Arquitectura General

```
┌──────────────────────────────────────────────────────────────────┐
│                        UKUCHA SYSTEM                             │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐     │
│  │ Fall Detector │  │ EPP Detector │  │  Rescue Detector   │     │
│  │ YOLOv8n      │  │ YOLOv8m SH17 │  │ YOLOv8s-seg DResp │     │
│  │ + MediaPipe  │  │ + ByteTrack  │  │ (cada N frames)    │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬─────────────┘     │
│         │                 │                  │                    │
│         └────────┬────────┴─────────┬────────┘                   │
│                  │                  │                             │
│         ┌───────▼──────┐  ┌───────▼──────────────┐              │
│         │ FUSION LAYER │  │  result.plot(canvas)  │              │
│         │ EPP x Rescue │  │  (mascaras DRespNeT)  │              │
│         └──────┬───────┘  └──────────────────────┘              │
│                │                                                 │
│    ┌───────────┴────────────────────────────┐                   │
│    │  6 CLASIFICACIONES DE ESCENARIO        │                   │
│    │  1. Caida normal                       │                   │
│    │  2. Persona bajo escombros (bodypart)  │                   │
│    │  3. Victima en escombros (completa)    │                   │
│    │  4. Civil detectado (DRespNeT)         │                   │
│    │  5. Caida en escombros                 │                   │
│    │  6. Zona de escombros (sin persona)    │                   │
│    └───────────┬────────────────────────────┘                   │
│                │                                                 │
│    ┌───────────┴──────────┐  ┌──────────────────┐               │
│    │  Evidencia           │  │  Server (FastAPI) │               │
│    │  snapshots + CSV     │  │  notificaciones   │               │
│    └──────────────────────┘  └──────────────────┘               │
│                                                                  │
│    ┌─────────────────────────────────────────────┐               │
│    │  Robot Autonomo (ESP32-S3)                  │               │
│    │  GPS + gas/polvo + camara + audio            │               │
│    └─────────────────────────────────────────────┘               │
└──────────────────────────────────────────────────────────────────┘
```

## Archivos del Proyecto

```
ukucha-fall-detector/
├── ukucha_detector.py          # Pipeline unificado (3 detectores + fusion)
├── webcam_fall.py              # Fall detector standalone (NO importa de detectors/)
├── server.py                   # FastAPI backend (telemetria + detecciones)
├── requirements.txt            # Dependencias pinneadas
├── detectors/
│   ├── fall_detector.py        # Clase FallDetector (reusable)
│   ├── epp_detector.py         # Clase EppDetector (reusable)
│   └── rescue_detector.py      # Clase RescueDetector (reusable)
├── backend/                    # Pipeline WiFi+deteccion+WS+Supabase (hardware ESP32)
│   ├── schemas/                 # Modelos de datos (frames, eventos, telemetria)
│   ├── ports/                   # Interfaces (Ports & Adapters)
│   ├── adapters/                # Implementaciones (UDP/MJPEG, Supabase, mock)
│   ├── services/                # Logica de orquestacion
│   ├── api/                     # Rutas WebSocket/HTTP
│   └── app.py                   # Entry point del backend -- ver ukucha/backend-conexion.md
├── models/
│   ├── yolov8n.pt              # Personas (COCO, descarga automatica)
│   ├── epp_yolo8m.pt           # EPP 17 clases SH17
│   └── drespnet_best.pt        # Escombros 11 clases DRespNeT
├── outputs/detections/         # Snapshots + CSV de victimas confirmadas
└── .claude/skills/ukucha/      # Estos skills
```

## Dos Fuentes de Frames para el Pipeline de Deteccion

Existen dos formas de alimentar el pipeline de deteccion (FallDetector,
EppDetector, RescueDetector + fusion `classify_rubble_victims()` etc. de
`ukucha_detector.py`):

1. **Webcam standalone** — `ukucha_detector.py` / `webcam_fall.py` leen
   directamente de una camara local via `WebcamStream` (OpenCV). Sigue
   funcionando de forma independiente, sin depender de `backend/`.
2. **Hardware ESP32 (WiFi)** — `backend/` obtiene frames del ESP32-CAM
   (stream HTTP MJPEG) y sensores/comandos del ESP32-S3 de campo (UDP),
   ambos conectados por WiFi al mismo hotspot que la laptop del backend
   -- sin USB/serial, ver `.claude/skills/ukucha/backend-conexion.md` --
   y alimenta la MISMA capa de deteccion y fusion que el modo webcam. Solo
   cambia la FUENTE del frame; los detectores y la logica de clasificacion
   de escenarios son compartidos entre ambos modos.

Detalle completo de `backend/` (arquitectura Ports & Adapters, threading,
rutas WebSocket, persistencia Supabase, etc.): ver `ukucha/backend-conexion.md`.

## Constantes de Color (BGR) — ukucha_detector.py

```python
COL_ROUTE         = (0, 255, 255)    # amarillo — linea de ruta de rescate
COL_RUBBLE_VICTIM = (180, 0, 180)    # magenta — persona bajo escombros
COL_RUBBLE_ZONE   = (0, 140, 140)    # teal — zona de escombros sin persona
COL_BLOCKED       = (0, 0, 180)      # rojo oscuro — acceso bloqueado
COL_CIVILIAN      = (200, 100, 0)    # azul-naranja — civil detectado por DRespNeT
COL_INDICIO       = (0, 165, 255)    # ambar — indicios de persona (bodyparts aisladas)
```

## Constantes Nombradas — ukucha_detector.py

```python
DET_DIR = Path(__file__).resolve().parent / "outputs" / "detections"
CONFIRM_FRAMES = 3   # frames que una victima debe persistir para registrarse
DEDUP_IOU = 0.3      # IoU minimo para considerar que dos bboxes son la misma persona
PRUNE_INTERVAL = 300 # podar cada N frames (~10s a 30fps)  — definida dentro de main()
PRUNE_STALE = 900    # borrar IDs no vistos en N frames (~30s) — definida dentro de main()
```

`PRUNE_INTERVAL` y `PRUNE_STALE` son variables locales de `main()` (no constantes de
modulo como las demas), pero cumplen el mismo rol de configuracion fija.

## BODYPART_ES — Diccionario de Traduccion

Definido de forma independiente y duplicada en `ukucha_detector.py` y en
`detectors/epp_detector.py` (mismo contenido, sin import compartido):

```python
BODYPART_ES = {
    "head": "cabeza",
    "face": "rostro",
    "hands": "manos",
    "foot": "pie",
}
```

## WebcamStream — Captura en Hilo Aparte

```python
class WebcamStream:
    def __init__(self, src=0):
        self.cap = cv2.VideoCapture(src)
        # si no abre: running=False, mensaje de error con el indice pedido
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.ret, self.frame = self.cap.read()   # primer frame sincronico
        self._lock = threading.Lock()
        self.thread = threading.Thread(target=self.update, args=())
        self.thread.daemon = True                # hilo daemon: no bloquea salida del proceso
        self.thread.start()

    def update(self):
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                with self._lock:
                    self.ret, self.frame = ret, frame
            time.sleep(0.005)   # cede CPU, evita busy-loop a 100%

    def read(self):
        with self._lock:
            if self.frame is None:
                return False, None
            return self.ret, self.frame.copy()   # copia bajo lock: thread-safe,
                                                    # evita que el loop principal lea
                                                    # un frame mutado a mitad de escritura
```

Resolucion fija 1280x720 solicitada via `CAP_PROP_FRAME_WIDTH`/`HEIGHT` (la
camara puede ignorarla si no la soporta). `read()` siempre devuelve una copia
(`.copy()`), nunca una referencia directa al buffer interno.

## pick_device() — Seleccion de Dispositivo

```python
def pick_device():
    try:
        import torch
        return 0 if torch.cuda.is_available() else "cpu"
    except Exception:
        return "cpu"
```

Intenta `torch.cuda.is_available()`; retorna `0` (indice de GPU para
ultralytics) si hay CUDA disponible, `"cpu"` en cualquier otro caso (incluye
`ImportError` si torch no esta instalado). Se imprime en consola como
`cuda:0` o `cpu` segun corresponda.

## Validacion de Modelos al Inicio

Antes de instanciar los detectores, `main()` arma la lista de modelos
requeridos segun que capas esten activas (`--no-fall`/`--no-epp`/`--no-rescue`)
y verifica que cada archivo exista en `models/`:

```python
required_models = []
if not args.no_fall:   required_models.append(("yolov8n.pt", "fall detector"))
if not args.no_epp:    required_models.append(("epp_yolo8m.pt", "EPP detector"))
if not args.no_rescue: required_models.append(("drespnet_best.pt", "rescue detector"))
for fname, desc in required_models:
    if not (models_dir / fname).exists():
        print(f"ERROR: no se encontro models/{fname} (requerido por {desc}).")
        print(f"  Colocar el archivo en: {models_dir / fname}")
        return
```

Si falta un modelo requerido, el programa imprime el nombre del archivo, la
capa que lo necesita, y la ruta absoluta exacta donde debe colocarse, y
termina (`return`) sin abrir camara ni cargar ningun modelo.

## Ventana y HUD

Nombre exacto de la ventana OpenCV: `"UKUCHA - Deteccion Integral (caidas + EPP + rescate)"`
(`cv2.WINDOW_NORMAL`, resize a 1280x720).

### banner()

```python
def banner(frame, text, y, color=(255, 255, 255)):
    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
    cv2.rectangle(frame, (5, y - th - 6), (15 + tw, y + 4), (0, 0, 0), -1)
    cv2.putText(frame, text, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)
```

Dibuja un rectangulo negro solido de fondo (padding: 5px izquierda, 6px arriba
del texto, 15px derecha, 4px abajo) y el texto encima. `y` es la coordenada
base del texto (no del rectangulo); se usa para apilar banners en lineas fijas
(28, 56, 84, 112...).

### Gramatica del Banner de Bodyparts

```python
partes_unicas = sorted(set(BODYPART_ES.get(nm, nm) for _, nm, _ in bodyparts))
if len(partes_unicas) == 1:
    detalle = partes_unicas[0]
else:
    detalle = ", ".join(partes_unicas[:-1]) + " y " + partes_unicas[-1]
banner(frame, f"INDICIO DE PERSONA - {detalle} detectada(s)", 112, COL_INDICIO)
```

- 1 parte unica: `"cabeza detectada(s)"` (sin coma ni "y").
- 2+ partes unicas: todas separadas por coma excepto la ultima, unida con
  `" y "` — ej. `"cabeza, manos y pie detectada(s)"`.
- El sufijo `"detectada(s)"` es literal y fijo, no varia con la cantidad
  (no hay pluralizacion real del verbo, solo el `(s)` entre parentesis).
- `partes_unicas` viene de un `set()` ordenado alfabeticamente
  (`sorted`), por lo que el orden de aparicion NO respeta el orden de
  deteccion sino el alfabetico en español.

## Pipeline Unificado — ukucha_detector.py

### Flujo por Frame

```
1. WebcamStream.read() → frame (hilo aparte, sin lag)
2. infer_frame = frame.copy()   # copia LIMPIA para inferencia
3. FallDetector.process(infer_frame, canvas=frame)
4. RescueDetector.process(infer_frame) cada N frames
   └── extract_access() → accesos transitables
   └── extract_hazards() → rubble, civilians, rescue_teams, blocked
   └── result.plot(img=frame) → mascaras/cajas DRespNeT
5. EppDetector.process(infer_frame, canvas=frame)
   └── victims (tid, bbox, confirmable)
   └── bodyparts (tid, name, bbox) — partes aisladas
6. FUSION:
   └── link_victims_access() → rutas de rescate
   └── classify_rubble_victims() → escenarios de escombros
   └── draw_blocked_access() → accesos bloqueados con X
7. EVIDENCIA: confirmar victimas persistentes → snapshot + CSV
8. NOTIFICACIONES: enviar eventos al server (borde de subida)
9. HUD: FPS, contadores, alertas, banner de indicios
```

### Separacion infer_frame / canvas

CRITICO: cada detector recibe `infer_frame` (limpio) para inferir y `frame`
(canvas) para dibujar. Si se infiere sobre un frame ya anotado, el modelo
interpreta cajas/texto como parte de la escena — degrada deteccion en cadena.

### Patron de Reuso de DRespNeT entre Frames

DRespNeT (segmentacion) corre cada `--env-every` frames (default 5). Los
datos logicos (`accesses`, `hazards`, etc.) se REUSAN entre recalculos
porque el entorno fisico no cambia rapido. Pero el DIBUJO (`result.plot()`)
solo se aplica en el frame donde se recalculo — si se dibujara sobre frames
salteados, las cajas quedarian en posiciones de N frames atras.

## Rutas de Rescate — link_victims_access()

```python
def link_victims_access(frame, victims, accesses, max_dist):
    for _, vbox, _ in victims:
        vc = _center(vbox)
        best, best_d = None, 1e12
        for _, abox in accesses:
            ac = _center(abox)
            if _inside_box(ac, vbox):
                continue   # skip guard: el acceso esta DENTRO de la propia
                           # caja de la victima (falso "acceso" superpuesto,
                           # no una ruta real hacia otro punto)
            d = hypot(vc[0] - ac[0], vc[1] - ac[1])
            if d < best_d:
                best_d, best = d, abox
        if best is not None and best_d <= max_dist:
            # dibuja linea COL_ROUTE + texto "RUTA DE RESCATE" en el punto medio
            ...
```

Guard clave: si el centro del acceso cae DENTRO del bbox de la victima
(`_inside_box(ac, vbox)`), ese acceso se descarta para esa victima — evita
trazar una "ruta" de la victima hacia si misma cuando el acceso y la victima
se solapan espacialmente. Solo se conecta al acceso transitable mas cercano
que este fuera de la propia caja, y solo si la distancia esta dentro de
`max_dist` (`--route-frac * diagonal_del_frame`).

## _overlaps() — Helper de Superposicion

```python
def _overlaps(box_a, box_b):
    """True if center of box_a is inside box_b or IoU > 0.1."""
    ca = _center(box_a)
    if _inside_box(ca, box_b):
        return True
    return _iou(box_a, box_b) > 0.1
```

Dos condiciones alternativas (OR): (1) el CENTRO de `box_a` cae dentro de
`box_b` — util cuando `box_a` es pequeño (ej. un bodypart) y queda contenido
en un hazard grande; (2) IoU > 0.1 — umbral bajo deliberado para capturar
superposiciones parciales sin exigir gran solapamiento. Se usa en
`classify_rubble_victims()` para cruzar bodyparts/victimas/civiles/caidas
contra hazards de DRespNeT.

## Fusion EPP x DRespNeT — classify_rubble_victims()

Cruza detecciones de EPP (personas/bodyparts) con DRespNeT (escombros) para
clasificar escenarios. Usa `_overlaps()`: centro de box A dentro de box B,
o IoU > 0.1.

### Los 6 Escenarios

| # | Escenario | Deteccion | Color | Visual |
|---|---|---|---|---|
| 1 | Caida normal | FallDetector score alto, persona completa, SIN rubble | Rojo | Alertas existentes |
| 2 | Persona bajo escombros | EPP bodypart (cabeza/manos/pie) + rubble overlap | Magenta (180,0,180) | Borde grueso + label + alerta parpadeante |
| 3 | Victima en escombros | EPP persona completa + rubble overlap | Magenta | Borde + "VICTIMA EN ESCOMBROS" |
| 4 | Civil detectado | DRespNeT civilian_visible/group_of_civilians | Azul-naranja (200,100,0) | Label con confianza, + "BAJO ESCOMBROS" si rubble overlap |
| 5 | Caida en escombros | FallDetector EN EL SUELO/CAYENDO + rubble overlap | Rojo | "CAIDA EN ESCOMBROS" adicional |
| 6 | Zona de escombros | rubble/debris sin persona cerca | Teal (0,140,140) | Label informativo "ESCOMBROS: tipo" |

Accesos bloqueados: `entry_door_blocked`, `entry_window_blocked` → X roja sobre la caja, "BLOQUEADO: tipo".

### Banner de Indicios de Persona

Cuando hay bodyparts aisladas (sin rubble), aparece un banner ambar (0,165,255)
en y=112: `INDICIO DE PERSONA - cabeza y manos detectada(s)`. Traduccion
automatica via `BODYPART_ES = {head: cabeza, face: rostro, hands: manos, foot: pie}`.

## Filtro Anatomico — es_plausible_humano()

En `detectors/fall_detector.py`. YOLO (COCO) confunde objetos con forma
humanoide (silla+manta, ropa colgada) con personas. MediaPipe SIEMPRE
devuelve 33 landmarks (nunca falla), asi que fuerza un esqueleto con
geometria imposible.

Verifica ratio ancho_hombros / alto_torso usando world landmarks 3D.
Rango: 0.15 - 3.0 (deliberadamente amplio para no rechazar personas reales).
Si falla: caja gris con "objeto? no-humano".

## Deduplicacion de Victimas — _same_person()

Combina IoU >= 0.3 OR distancia de centros <= 0.5 * diagonal promedio.
Solo IoU falla cuando la persona gesticula/se mueve (bbox cambia forma).

## Sistema de Evidencia

### Confirmacion de Victimas

- Track ID estable (ByteTrack del EPP detector)
- Solo `confirmable=True` (persona completa, no bodypart aislada)
- Persistir N frames (`CONFIRM_FRAMES=3`) antes de confirmar
- Dedup espacial con `_same_person()` y `logged_boxes`
- Al confirmar: snapshot JPEG + fila en CSV + print + server notification

### Archivos de Salida

```
outputs/detections/
├── detections_log.csv           # timestamp, victim_id, snapshot
├── victima_42_20260718_153045.jpg
└── ...
```

### Poda de Memoria

Cada 300 frames (~10s a 30fps), limpiar IDs no vistos en 900 frames (~30s).
Evita memory leak de `victim_seen` y `victim_last_frame`.

## Notificaciones al Server

Via `ServerNotifier` (hilo daemon, cola acotada maxsize=20, no bloqueante).
Envio por borde de subida (no cada frame):

| Evento | tipo | Cuando |
|---|---|---|
| Victima confirmada | `victima_confirmada` | Evidencia generada |
| Caida detectada | `caida_detectada` | Transicion a alerta |
| Caida critica | `caida_critica` | Transicion a critica (>5s suelo) |
| Persona bajo escombros | `persona_bajo_escombros` | Transicion de 0 a >0 rubble victims |
| Caida en escombros | `caida_en_escombros` | Transicion de 0 a >0 fall+rubble |

## CLI — Argumentos

```bash
venv\Scripts\python.exe ukucha_detector.py [opciones]
```

| Argumento | Default | Descripcion |
|---|---|---|
| `--cam N` | 0 | Indice de camara |
| `--conf-victim F` | 0.25 | Umbral personas/bodyparts (recall) |
| `--conf-epp F` | 0.30 | Umbral EPP rescatista (precision) |
| `--conf-env F` | 0.35 | Umbral DRespNeT |
| `--env-every N` | 5 | DRespNeT cada N frames |
| `--route-frac F` | 0.35 | Distancia max victima-acceso (fraccion diagonal) |
| `--show-all-epp` | False | Mostrar EPP menor (guantes, gafas...) |
| `--no-fall` | False | Desactivar capa de caidas |
| `--no-epp` | False | Desactivar capa de EPP |
| `--no-rescue` | False | Desactivar capa de entorno |
| `--server-url URL` | None | URL de server.py para notificaciones |

Validacion: todos los floats se clampean a [0.0, 1.0], env-every a min 1.

## Jerarquia Visual de Alertas

1. **Rojo parpadeante (4Hz)** — EMERGENCIA / PERSONA EN EL SUELO (>5s)
2. **Rojo** — CAIDA DETECTADA
3. **Magenta parpadeante (3Hz)** — PERSONA BAJO ESCOMBROS
4. **Ambar fijo** — INDICIO DE PERSONA (bodyparts sin rubble)
5. **Teal** — ZONA DE ESCOMBROS (informativo)
6. **Rojo oscuro + X** — ACCESO BLOQUEADO

### HUD (3-4 lineas top-left)

```
FPS: 25.3                                              (verde)
VICTIMAS: 2 (unicas conf.: 1)  RESCATISTAS: 0  EPP: 0 (rojo si hay victimas)
ENTORNO: 4  RUTAS: 1  BAJO ESCOMBROS: 1  BLOQUEADOS: 2 (magenta/cyan/gris)
INDICIO DE PERSONA - manos detectada(s)                 (ambar, solo si hay bodyparts)
```

## Stack de Software

```
Python 3.12 (venv local: venv\Scripts\python.exe)
ultralytics==8.2.81           # YOLOv8
mediapipe==0.10.14            # Pose estimation
opencv-contrib-python==4.11.0.86
fastapi==0.139.2              # API server
torch==2.6.0+cu124            # CUDA 12.4 (RTX 4050 Laptop, 6GB VRAM)
lap==0.5.13                   # ByteTrack tracking
numpy==1.26.4                 # Pinneado (ultralytics <2.0.0 requiere <2.x)

# Dependencias nuevas por backend/ (ver ukucha/backend-conexion.md)
# Sin pyserial: el enlace con los nodos ESP32 es 100% WiFi (UDP + HTTP
# MJPEG), nunca USB -- backend/adapters/serial_transport.py queda solo
# como referencia historica sin uso, no aporta una dependencia real.
supabase==2.31.0              # Persistencia (+ postgrest, realtime, storage3,
postgrest==2.31.0             #   supabase-auth, supabase-functions como
realtime==2.31.0              #   dependencias transitivas, mismas versiones)
storage3==2.31.0
supabase-auth==2.31.0
supabase-functions==2.31.0
httpx2==2.7.0                 # Requeridos por starlette.testclient (smoke
httpcore2==2.7.0              #   tests del backend), coexisten con httpx/
truststore==0.10.4            #   httpcore normales sin pisarlos
python-dotenv==1.2.2          # Carga de config desde .env
```

VRAM estimada: yolov8n ~6MB + yolo8m ~100MB + yolov8s-seg ~45MB + MediaPipe CPU = ~200MB total.

## Hardware — Robot Autonomo (ESP32-S3)

### Componentes

| Componente | Cantidad | Funcion |
|---|---|---|
| ESP32-S3 | 2 | Microcontroladores (control + percepcion) |
| GPS Ublox NEO-M8N | 1 | Posicionamiento |
| Driver TB6612FNG | 2 | Control de 4 motores DC |
| Motoreductores | 4 | Traccion 4WD |
| TOF VL53L0X | 1 | Distancia/obstaculos (0-2m) |
| Sensor polvo | 1 | Particulas PM2.5 |
| MQ-2 | 1 | Gas combustible/humo |
| MQ-135 | 1 | CO2, NH3, calidad aire |
| Camara OV7670 | 1 | Vision del robot |
| WS2812B | 1 | LEDs indicadores |
| INMP441 | 2 | Microfonos I2S (pendiente) |

### Distribucion ESP32s

```
ESP32 #1 — CONTROL: TB6612FNG x2, GPS, VL53L0X, polvo, MQ-2, MQ-135, WS2812B
ESP32 #2 — PERCEPCION: OV7670, INMP441 x2, WiFi → server FastAPI
```

### Protocolo Robot → Server

```
POST /api/telemetria   → sensores, GPS, alertas
POST /api/frame        → imagen JPEG del robot
POST /api/deteccion    → eventos de deteccion (desde ukucha_detector.py)
GET  /api/detecciones  → historial de detecciones
```

### Limites de Gas (D.S. 024-2016-EM Peru)

| Gas | TWA | STEL | Sensor |
|---|---|---|---|
| CO | 25 ppm | 50 ppm | MQ-2 |
| NO2 | 3 ppm | 5 ppm | MQ-135 |
| CO2 | 5000 ppm | 30000 ppm | MQ-135 |
| H2S | 10 ppm | 15 ppm | MQ-2 |

## Convenciones del Proyecto

- Entorno virtual: SIEMPRE `venv\Scripts\python.exe` (Windows), nunca python global
- Codigo fuente: ingles (variables, funciones, comentarios)
- UI labels en pantalla: espanol
- Commits: conventional commits en espanol, sin Co-Authored-By (ver `commits.md`)
- Cada detector = modulo standalone + clase reusable
- Separar infer_frame (limpio, inferencia) de canvas (anotaciones)
- Pesos del modelo en `models/`, listados en `.gitignore`

## Ver Tambien

- `ukucha/backend-conexion.md` — pipeline `backend/` (serial ESP32 + WS + Supabase)
