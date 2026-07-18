# Skill: UKUCHA EPP Detector — Clasificacion Victima/Rescatista

## Objetivo

Detectar personas y clasificarlas segun EPP (Equipo de Proteccion Personal):
**VICTIMA** (sin EPP) vs **RESCATISTA** (con casco/chaleco/traje). Reporta
partes de cuerpo aisladas (cabeza, manos, pie, rostro) como posibles victimas
parcialmente visibles. Integra con DRespNeT via el orquestador para detectar
personas bajo escombros.

Este documento permite regenerar `detectors/epp_detector.py` desde cero.

## Modelo

- Pesos: `models/epp_yolo8m.pt` (YOLOv8m)
- Dataset: SH17 (17 clases), entrenado por el equipo
- Clases utiles en practica: `helmet`, `ear-mufs`, `gloves`, `safety-vest`

### Construccion del path del modelo

```python
from pathlib import Path
MODELO_EPP = str(Path(__file__).resolve().parents[1] / "models" / "epp_yolo8m.pt")
```

`parents[1]` sube desde `detectors/` a la raiz del proyecto, por lo que el
path resuelve correctamente sin importar el `cwd` desde el que se ejecute.

### Todas las Clases (model.names)

```
person, ear, ear-mufs, face, face-guard, face-mask, foot, tool,
glasses, gloves, helmet, hands, head, medical-suit, shoes,
safety-suit, safety-vest
```

## Categorias de Clasificacion

```python
PERSON_CLASS = "person"
BODYPART = {"head", "face", "hands", "foot"}
RESCUER_SIGNAL = {"helmet", "safety-vest", "safety-suit", "medical-suit"}
EQUIP_OTHER = {"gloves", "face-mask", "face-guard", "glasses", "shoes", "ear-mufs", "tool"}
```

## Traduccion a Español (Labels en Pantalla)

```python
BODYPART_ES = {"head": "cabeza", "face": "rostro", "hands": "manos", "foot": "pie"}
```

Los labels en pantalla usan español: "VICTIMA? manos #280" (no "hands").

## Colores (BGR, OpenCV)

```python
COL_VICTIM = (0, 0, 255)      # rojo
COL_RESCUER = (0, 200, 0)     # verde
COL_EQUIP = (0, 165, 255)     # naranja
```

Tuplas en formato BGR (no RGB), como espera `cv2.rectangle`/`cv2.putText`.

## Umbrales

| Parametro | Default | Razon |
|---|---|---|
| `conf_victim` (CONF_VICTIM_DEFAULT) | 0.25 | Bajo = mas recall detectando personas |
| `conf_epp` (CONF_EPP_DEFAULT) | 0.30 | Bajado de 0.45 a 0.30 porque indoor el casco daba conf 0.20-0.44 |
| `show_all_epp` | False | Solo EPP "fuerte" por defecto |

## Funciones Auxiliares (modulo, fuera de la clase)

```python
def _center(xyxy):
    """Centro (x, y) de una caja [x1, y1, x2, y2]."""
    x1, y1, x2, y2 = xyxy
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


def _inside(pt, box):
    """True si el punto pt=(x, y) cae dentro de box=[x1, y1, x2, y2]."""
    x1, y1, x2, y2 = box
    return x1 <= pt[0] <= x2 and y1 <= pt[1] <= y2


def _box_id(b):
    """Devuelve el track id de una box, o None si el tracker no lo asigno."""
    if getattr(b, "id", None) is None:
        return None
    try:
        return int(b.id[0])
    except Exception:
        return None


def _label_box(frame, box, color, text):
    """Dibuja el borde de la caja + fondo de texto relleno + texto blanco."""
    x1, y1, x2, y2 = map(int, box)
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
    cv2.rectangle(frame, (x1, y1 - th - 6), (x1 + tw + 4, y1), color, -1)
    cv2.putText(frame, text, (x1 + 2, y1 - 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
```

- `_box_id()`: usa `getattr(b, "id", None)` primero (evita AttributeError si
  el atributo no existe), luego `int(b.id[0])` dentro de un `try/except`
  generico — cubre `IndexError` (id vacio) y `TypeError` (id no indexable).
  Devuelve `None` en cualquiera de esos casos en vez de propagar la excepcion.
- `_label_box()`: dibuja en 3 pasos sobre `frame` (puede ser `infer_frame` o
  `canvas`, in-place) — (1) rectangulo de borde con `color` y grosor 2, (2)
  rectangulo relleno (`-1`) del mismo `color` como fondo de texto, calculado
  con `cv2.getTextSize`, (3) el `text` en blanco `(255, 255, 255)` encima.

## Algoritmo de Clasificacion

1. Correr YOLO en modo `track()` con `tracker="bytetrack.yaml"`, `persist=True`
   (requiere paquete `lap==0.5.13`). Umbral: `min(conf_victim, conf_epp)`.
   Si `process(..., track=False)`, se usa `self.model.predict(...)` en su
   lugar (mismo umbral, sin IDs de tracking) — fallback explicito para casos
   donde no se necesita tracking (p.ej. frames sueltos, tests).
2. Separar detecciones en 3 grupos:
   - `persons`: clase `person`, conf >= conf_victim
   - `parts`: clases BODYPART, conf >= conf_victim
   - `equip`: clases RESCUER_SIGNAL (+ EQUIP_OTHER si show_all_epp), conf >= conf_epp
3. Para cada persona: si el centro de algun EPP fuerte cae DENTRO del bbox
   → RESCATISTA (verde). Si no → VICTIMA (rojo).
4. Para cada bodypart AISLADA (centro fuera de CUALQUIER persona):
   → "VICTIMA? {parte_es}" (rojo), `confirmable=False`.
   → Se agrega a `isolated_parts` para la fusion con DRespNeT.
5. Dibujar EPP detectado en naranja con nombre + confianza.

## Retorno de process()

```python
{
    "victims": [(tid, bbox, confirmable), ...],
    # tid: int o None (track ID de ByteTrack)
    # bbox: [x1, y1, x2, y2] floats
    # confirmable: True = persona completa (genera evidencia)
    #              False = bodypart aislada (solo visual, no evidencia)

    "n_rescuer": int,   # cantidad de rescatistas detectados
    "n_epp": int,       # items de EPP detectados

    "bodyparts": [(tid, name, bbox), ...],
    # name: nombre en INGLES del modelo (head, hands, face, foot)
    # Solo bodyparts AISLADAS (fuera de personas)
    # Usado por el orquestador para fusion con DRespNeT
}
```

### Diferencia victims vs bodyparts

`victims` contiene TODAS las detecciones (personas completas + bodyparts aisladas).
`bodyparts` contiene SOLO las bodyparts aisladas con su nombre original del modelo
(necesario para la fusion EPP×DRespNeT en `classify_rubble_victims()`).

## Interfaz

```python
class EppDetector:
    def __init__(self, model_path=MODELO_EPP, device=None): ...
    def process(self, infer_frame, conf_victim=0.25, conf_epp=0.30,
                show_all_epp=False, track=True, canvas=None) -> dict:
        # infer_frame: frame LIMPIO para inferencia
        # canvas: frame para dibujar (si None, usa infer_frame)
```

## Standalone

```bash
venv\Scripts\python.exe detectors/epp_detector.py
```

Abre webcam, muestra victimas/rescatistas/EPP con FPS. Tecla 'q' para salir.
El standalone NO usa canvas separado (usa frame directamente).

### Comportamiento exacto del bloque `__main__`

1. Imprime `"Cargando EppDetector (yolo8m.pt)..."` y crea `EppDetector()`.
2. Abre `cv2.VideoCapture(0)`; si `not cap.isOpened()`, imprime
   `"ERROR: no se pudo abrir la camara."` y retorna sin entrar al loop.
3. Imprime `"Presiona 'q' para salir."`.
4. Loop principal (dentro de `try/finally` que libera la camara y cierra
   ventanas al salir):
   - Lee frame con `cap.read()`; si `not ret`, rompe el loop.
   - Llama `detector.process(frame)` (sin `canvas`, dibuja sobre el mismo
     frame capturado).
   - Calcula FPS instantaneo: `1.0 / max(now - prev_time, 1e-6)`.
   - Dibuja overlay en verde `(0, 255, 0)` en `(10, 30)` con
     `cv2.FONT_HERSHEY_SIMPLEX` escala 0.6, texto:
     `"FPS: {fps:.1f}  Victimas: {n}  Rescatistas: {n_rescuer}  EPP: {n_epp}"`.
   - Muestra la ventana `"EPP Detector (standalone)"` con `cv2.imshow`.
   - Sale del loop si `cv2.waitKey(1) & 0xFF == ord('q')`.
5. En el `finally`: `cap.release()` + `cv2.destroyAllWindows()`.

## Bugs Conocidos y Soluciones

- **conf_epp=0.45 es MUY alto para indoor**: casco/chaleco con webcam
  terrestre dan conf 0.20-0.44. Se bajo a 0.30.
- **ByteTrack reasigna IDs tras oclusion**: una persona que sale y vuelve
  al campo de vision puede obtener un ID nuevo. `_same_person()` en el
  orquestador mitiga esto con dedup espacial.
- **NO usar predict() para tracking en vivo**: pierde IDs entre frames.
- **NO usar el mismo umbral para persona y EPP**: recall bajo para personas
  si se usa umbral alto, precision baja para EPP si se usa umbral bajo.
- **Bodyparts dentro de persona NO cuentan aparte**: evita doble conteo.

## Verificacion

1. `python detectors/epp_detector.py` → webcam abre, no crashea
2. Persona sin nada → VICTIMA (rojo)
3. Con casco → RESCATISTA (verde)
4. Solo manos visibles → "VICTIMA? manos #N" (rojo, confirmable=False)
5. IDs estables mientras la persona se mueve

## Referencias

- Script original: `run_ukucha_dual.py` (funcion `analyze_people`) del
  repo del compañero (Anderbstz/data)
- Skills relacionadas: `ukucha/rescue-detector.md`, `ukucha/fall-detector.md`
