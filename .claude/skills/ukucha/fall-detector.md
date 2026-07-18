# Skill: UKUCHA Fall Detector — Deteccion de Caidas en Tiempo Real

## Objetivo

Detectar caidas de personas en tiempo real usando YOLOv8 (deteccion de personas)
+ MediaPipe Pose (estimacion de postura 2D + 3D). Sistema de 5 senales
ponderadas, maquina de 5 estados, tracking IoU, filtro anatomico anti-falsos
positivos, y alerta escalada.

Este documento permite regenerar el detector de caidas desde cero.

## Archivos

- `detectors/fall_detector.py` — Clase `FallDetector` reusable (importada por
  `ukucha_detector.py` para el pipeline unificado)
- `webcam_fall.py` — Entry-point standalone (mantiene su PROPIA copia de la
  logica, NO importa de `detectors/`). Se mantiene intacto como fallback.

## Dependencias

```
ultralytics==8.2.81    # YOLOv8 (clase 0 = persona)
mediapipe==0.10.14     # Pose estimation 2D + 3D world landmarks
opencv-contrib-python==4.11.0.86
numpy==1.26.4
```

Modelo YOLO: `models/yolov8n.pt` (anclado a models/, no depende de cwd).

MediaPipe Pose se instancia con:

```python
self.pose = mp_pose.Pose(
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5,
)
```

(en `webcam_fall.py` es el mismo config, pasado como context manager `with
mp_pose.Pose(...) as pose:`).

## Pipeline Completo

```
Frame (infer_frame limpio)
    │
    ▼
YOLO v8n (clase 0, conf >= 0.40)
    │
    ├── Filtro: alto >= 60px (MIN_ALTO_BBOX), ancho >= 20px (inline, sin constante nombrada)
    ├── Filtro: aspect ratio >= 0.20
    ├── Filtro: cache no-persona (5 frames sin pose → objeto gris)
    │
    ▼
Crop persona → MediaPipe Pose
    │
    ├── Sin landmarks → marcar sin_pose, skip
    ├── Con landmarks:
    │
    ▼
evaluar_visibilidad()
    │
    ├── > 70% frame → "MUY CERCA" (skip)
    ├── hombros + caderas → "completo"
    ├── hombros + 2 body → "parcial" (~estado, sin alertas)
    └── menos → "insuficiente" (skip)
    │
    ▼
es_plausible_humano(landmarks, world_landmarks)     ← NUEVO
    │
    ├── Ratio hombros/torso fuera de [0.15, 3.0] → "objeto? no-humano" (skip)
    │
    ▼
calcular_score_caida(5 senales ponderadas)
    │
    ▼
detectar_sentado(geometria torso + piernas)
    │
    ▼
PersonState.update(score, sentado_geometrico)
    │
    ▼
Renderizado sobre canvas (NO sobre infer_frame)
```

## Constantes de Configuracion

```python
MODELO_YOLO = "models/yolov8n.pt"     # path anclado a models/
MIN_VISIBILIDAD = 0.5                  # landmarks principales
MIN_VISIBILIDAD_PARCIAL = 0.3         # landmarks secundarios
MIN_ALTO_BBOX = 60                     # px minimos de alto
MIN_KEYPOINTS_PARCIAL = 3             # DEFINIDA PERO NUNCA USADA (dead code,
                                        # presente tanto en fall_detector.py
                                        # como en webcam_fall.py)
MIN_CONFIANZA_YOLO = 0.40             # confianza minima YOLO
UMBRAL_SCORE_CAIDO = 0.40             # >= → EN EL SUELO
UMBRAL_SCORE_CAYENDO = 0.25           # >= → CAYENDO
DELTA_CAYENDO = 0.12                  # delta para detectar transicion
FRAMES_CONFIRMAR = 6                  # frames para confirmar (~200ms)
SEGUNDOS_ALERTA_CRITICA = 5           # segundos en suelo → EMERGENCIA
IOU_MIN_MATCH = 0.15                  # IoU bajo (bbox cambia en caida)
SCORE_SMOOTH_FRAMES = 3              # promedio movil
MAX_FRAMES_SIN_POSE = 5              # → objeto inanimado
MIN_ASPECT_HUMANO = 0.20             # aspect ratio minimo
```

## Las 5 Senales de Deteccion

### Senal 1: Angulo 3D del Torso (PESO: 0.35)

```
vector = promedio_3d(caderas) - promedio_3d(hombros)   ← CADERA - HOMBRO
angulo = arccos(dot(vector, [0,1,0]) / norm(vector))
normalizar(angulo, 25°, 55°)
```

BUG CRITICO: debe ser `cadera - hombro`, NO al reves (da ~180° para personas paradas).

### Senal 2: Extension de Piernas (PESO: 0.25)

```
ratio = (rodilla_y - cadera_y) / alto_torso
> 0.7 → 0.0 (de pie)  |  < 0.15 → 1.0 (caido)
```

### Senal 3: Compactacion Vertical (PESO: 0.15)

```
compactacion = spread_y / spread_x  (de landmarks 2D visibles, min 6)
>= 1.5 → 0.0 (vertical)  |  <= 0.5 → 1.0 (horizontal)
```

Requiere `spread_x > 10px` y landmarks dentro del frame (0.05 < x < 0.95).

### Senal 4: Angulo 2D Cabeza-Tobillos (PESO: 0.15)

```
angulo = abs(90 - degrees(atan2(tobillo_y - nariz_y, tobillo_x - nariz_x)))
normalizar(angulo, 30°, 60°)
```

### Senal 5: Aspect Ratio BBox (PESO: 0.10)

```
aspect = alto / ancho
>= 1.3 → 0.0  |  <= 0.5 → 1.0
```

Peso bajo porque engaña con personas sentadas.

### Score Final

`score = sum(senal_i * peso_i) / sum(pesos disponibles)` — normalizacion
dinamica permite funcionar con senales faltantes.

## _landmark_en_frame() — Utilidad de Validacion de Borde

```python
def _landmark_en_frame(lm_entry):
    """Verifica que el landmark este dentro del frame (no hallucinado en bordes)."""
    return 0.05 < lm_entry.x < 0.95 and 0.05 < lm_entry.y < 0.95
```

Funcion standalone (no metodo de clase) usada como filtro compuesto junto con
`_vis()`/`_vis_parcial()` en tres lugares: `evaluar_visibilidad()` (conteo de
hombros/caderas/cuerpo real), el calculo de `visibles` para la señal de
compactacion en `calcular_score_caida()`, y de forma implicita en cualquier
landmark que se use para senales geometricas. Recibe un unico landmark
(`lm_entry`, con atributos `.x`/`.y` normalizados 0-1) y rechaza los que caen
en el 5% de margen de cada borde — MediaPipe puede "alucinar" coordenadas para
puntos ocluidos o fuera de camara en vez de marcarlos como no visibles, y ese
margen filtra esos casos aunque la visibilidad reportada sea alta.

## Filtro Anatomico — es_plausible_humano()

YOLO (COCO generico) confunde objetos humanoide (silla+manta, ropa colgada)
con personas. MediaPipe SIEMPRE devuelve 33 landmarks, forzando un esqueleto
con geometria imposible.

```python
def es_plausible_humano(landmarks, wl):
    # Necesita: 2 hombros + al menos 1 cadera visibles
    # Calcula: ancho_hombros (3D, x-z) / alto_torso (3D, norma completa)
    # Rango valido: 0.15 <= ratio <= 3.0
    # Fuera del rango → False (no humano)
```

Si falla: caja gris con "objeto? no-humano", se descarta sin actualizar estado.

## Deteccion Geometrica de SENTADO

Independiente del score (sentado con torso vertical da score ~0.10, igual que de pie).

```
1. torso angulo > 30° → NO sentado
2. Si rodillas visibles: ratio pierna < 0.5 → SENTADO
3. Si rodillas NO visibles: distancia torso normalizada > 0.3 → SENTADO
```

## Maquina de 5 Estados

| Estado | Color BGR | Significado |
|---|---|---|
| DE PIE | (0,200,0) verde | Sin riesgo |
| SENTADO | (0,200,200) amarillo | Torso vertical, piernas dobladas |
| CAYENDO | (0,165,255) naranja | Transicion activa |
| EN EL SUELO | (0,0,255) rojo | Caida confirmada |
| RECUPERANDOSE | (255,165,0) naranja-azul | Levantandose |

Color parcial: `(200,200,0)`, prefijo `~` en el estado.

### Transiciones

- Histeresis 0.05 para salir de EN EL SUELO (score debe bajar a 0.35, no 0.39)
- Delta > 0.12 desde DE PIE/SENTADO → CAYENDO
- Delta < -0.12 desde EN EL SUELO → RECUPERANDOSE
- Suavizado: promedio movil 3 frames

### Alertas

- `caida_confirmada`: ultimos 6 frames TODOS en CAYENDO/EN EL SUELO, modo completo
- `alerta_critica`: >5 segundos en suelo, modo completo

## Interfaz — FallDetector

```python
class FallDetector:
    def __init__(self, model_path=MODELO_YOLO, device=None): ...

    def process(self, infer_frame, now, mostrar_landmarks=True,
                device=None, canvas=None) -> dict:
        # infer_frame: frame LIMPIO para inferencia
        # canvas: frame para dibujar (si None, usa infer_frame)
        # Retorna:
        # {
        #   "hay_alerta": bool,
        #   "hay_critica": bool,
        #   "personas": [{"pid", "bbox", "estado", "score", "modo"}, ...]
        # }

    def close(self):
        # Cierra MediaPipe Pose (libera recursos)
```

## Tracker por IoU (PersonTracker)

```
1. Calcular IoU de cada bbox actual vs previos
2. Filtrar IoU >= 0.15
3. Greedy matching (IoU descendente, sin repetir)
4. Sin match → nueva PersonState
5. Previos sin match → eliminar
```

IoU bajo (0.15) porque bbox cambia drasticamente durante caida (vertical → horizontal).

### Cache No-Persona

5 frames sin pose → objeto. Se muestra con borde gris fino, sin procesamiento.
Si MediaPipe encuentra pose de nuevo → reset contador.

## Bugs Conocidos

| Bug | Causa | Solucion |
|---|---|---|
| Angulo ~180° parado | vector `hombro - cadera` | Usar `cadera - hombro` |
| Landmarks hallucinados | MediaPipe inventa en bordes | `_landmark_en_frame()`: 0.05 < x < 0.95 |
| SENTADO oscila | Score fluctua ±0.02 | Suavizado 3 frames + histeresis 0.05 |
| Sentado → EN EL SUELO | Bbox cuadrado infla score | Deteccion geometrica separada |
| Tracking perdido en caida | IoU alta pierde bbox cambiante | IoU minimo 0.15 |
| Objeto como persona | YOLO COCO falso positivo | `es_plausible_humano()` + cache 5 frames |

## Verificacion

1. Persona parada → DE PIE (verde), score < 0.15
2. Sentarse → SENTADO (amarillo), score bajo pero estado correcto
3. Caerse → CAYENDO → EN EL SUELO (rojo), alerta a los 6 frames
4. Quedarse en suelo >5s → EMERGENCIA parpadeante
5. Levantarse → RECUPERANDOSE → DE PIE
6. Silla/manta → "objeto? no-humano" (gris), sin alerta
7. Solo cara visible → PARCIAL (~estado), sin alerta

## Divergencias con webcam_fall.py

`webcam_fall.py` mantiene su PROPIA copia de la logica de deteccion (no
importa de `detectors/fall_detector.py`). El core matematico (las 5 senales,
`PersonState`, `PersonTracker`, umbrales) es identico byte-a-byte entre ambos
archivos, pero **NO es correcto decir "misma logica"** sin matices: hay
diferencias funcionales reales en el flujo de captura, CLI, y renderizado que
`FallDetector.process()` no replica y viceversa:

| Aspecto | `webcam_fall.py` | `detectors/fall_detector.py` (clase `FallDetector`) |
|---|---|---|
| `es_plausible_humano()` | **AUSENTE por completo** — no filtra objetos con geometria no-humana | Presente, descarta "objeto? no-humano" |
| CLI | `sys.argv` directo (`sys.argv[1]` como indice o ruta de video) | N/A — es una clase, el CLI vive en `ukucha_detector.py` (usa `argparse`) |
| Dibujo de landmarks | Dibuja sobre el crop `persona`, luego copia de vuelta: `frame[y1c:y2c, x1c:x2c] = persona` | Dibuja sobre una VISTA (`canvas_crop = canvas[y1c:y2c, x1c:x2c]`) — muta `canvas` in-place, sin copia posterior |
| Fullscreen | Toggle con tecla `'f'` via `cv2.WND_PROP_FULLSCREEN` / `cv2.setWindowProperty` | No existe (sin manejo de teclado propio, lo controla `ukucha_detector.py`) |
| Enumeracion de camaras | Si falla `cap.isOpened()`, escanea indices 0-4 y reporta resoluciones disponibles | No existe — `WebcamStream` de `ukucha_detector.py` solo reporta error del indice pedido |
| Warm-up de camara | 5x `cap.read()` descartados antes del loop principal | No existe |
| Fuente de video | Soporta indice de camara O ruta de archivo de video (`sys.argv[1]`, cae a `str` si no es `int`) | Solo recibe `infer_frame` ya capturado — la fuente la resuelve el caller |
| Locale | `os.environ["LC_ALL"] = "en_US.UTF-8"` al tope del modulo | No presente |
| Texto de pie de pagina | `"UKUCHA Fall Detector \| 'q' salir \| 'f' fullscreen"` | N/A (el pipeline unificado dibuja su propio footer: `"UKUCHA \| 'q' salir"`) |
| Posicion de alertas | Coordenadas absolutas: emergencia en `(30, 60)`/`(30, 100)`, caida en `(30, 70)` | Coordenadas relativas al alto del frame: `(30, h-90)`/`(30, h-55)`, caida en `(30, h-60)` |
| `_TORSO_LM` | Definida (`[LEFT_SHOULDER, RIGHT_SHOULDER, LEFT_HIP, RIGHT_HIP]`) pero, igual que `MIN_KEYPOINTS_PARCIAL`, no se usa en ningun calculo | No existe esta lista |
| Nombre de ventana | `"UKUCHA Fall Detector"` | N/A (usa `"UKUCHA - Deteccion Integral (caidas + EPP + rescate)"` desde `ukucha_detector.py`) |

Conclusion: el algoritmo de scoring/estados es identico, pero `webcam_fall.py`
es MENOS seguro (sin `es_plausible_humano()`) y MAS autonomo (maneja su propia
captura, CLI y ventana) que la clase reusable. No asumir que corregir un bug
en un archivo lo corrige en el otro — son copias independientes.

## Referencias

- webcam_fall.py: entry-point standalone, logica propia (no importa de detectors/)
- Skills relacionadas: `ukucha/epp-detector.md`, `ukucha/rescue-detector.md`
