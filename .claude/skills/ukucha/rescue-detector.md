# Skill: UKUCHA Rescue Detector — Entorno de Escombros, Civiles y Accesos

## Objetivo

Detectar el entorno de una zona de desastre/rescate usando las 11 clases del
modelo DRespNeT: escombros (rubble/debris 4 niveles), civiles visibles,
equipo de rescate, y accesos transitables/bloqueados (puertas/ventanas).

Se integra con el EPP detector via fusion cruzada en el orquestador para
clasificar personas bajo escombros, victimas en zonas de riesgo, y accesos
bloqueados.

Este documento permite regenerar `detectors/rescue_detector.py` desde cero.

## Modelo

- Pesos: `models/drespnet_best.pt` (YOLOv8s-seg, segmentacion con mascaras)
- Base: fine-tuning de `yolov8s-seg.pt` sobre DRespNeT filtrado a 11 clases
- Dataset: DRespNeT (Cranfield University, CC BY 4.0),
  https://arxiv.org/abs/2508.16016
- Metricas propias en test: Box mAP@50 ~= 0.30, Mask mAP@50 ~= 0.31

### Construccion del path del modelo

```python
from pathlib import Path
MODELO_DRESPNET = str(Path(__file__).resolve().parents[1] / "models" / "drespnet_best.pt")
```

`parents[1]` sube desde `detectors/` a la raiz del proyecto, por lo que el
path resuelve correctamente sin importar el `cwd` desde el que se ejecute
(igual que `MODELO_EPP` en `epp_detector.py`).

## CAVEAT CRITICO — Domain Shift

Modelo entrenado con **imagenes AEREAS (dron/UAV)**. Con camara
terrestre/horizontal hay domain shift significativo: la deteccion de
rubble/debris/accesos es menos confiable que en el paper (92.7% mAP con
28 clases). NO prometer deteccion perfecta en demo — limitacion conocida
que requiere re-entrenamiento con datos terrestres para mejorar.

## Las 11 Clases (IDs 0-10)

| ID | Clase | Grupo | Significado |
|---|---|---|---|
| 0 | `civilian_visible` | CIVILIAN | Civil visible individual |
| 1 | `group_of_civilians` | CIVILIAN | Grupo de civiles |
| 2 | `rescue_team` | RESCUE | Equipo de rescate |
| 3 | `rubble` | HAZARD | Escombros generales |
| 4 | `debris_heavy` | HAZARD | Escombro pesado |
| 5 | `debris_light` | HAZARD | Escombro liviano |
| 6 | `debris_moderate` | HAZARD | Escombro moderado |
| 7 | `entry_door_accessible` | ACCESS | Puerta transitable |
| 8 | `entry_door_blocked` | BLOCKED | Puerta bloqueada |
| 9 | `entry_window_accessible` | ACCESS | Ventana transitable |
| 10 | `entry_window_blocked` | BLOCKED | Ventana bloqueada |

Estos IDs (0-10) son los asignados por `model.names` en runtime (dict
`{id: nombre}` que trae el propio checkpoint `drespnet_best.pt`) — dependen
del orden de clases fijado durante el entrenamiento/fine-tuning, NO estan
hardcodeados en `rescue_detector.py`. El codigo siempre resuelve el nombre
via `names.get(int(b.cls[0]), str(int(b.cls[0])))`, nunca por indice fijo.
La tabla de arriba documenta el mapeo actual del checkpoint entrenado por el
equipo, pero un reentrenamiento podria reordenar los IDs.

## Constantes de Grupo

```python
ACCESS_CLASSES = {"entry_door_accessible", "entry_window_accessible"}
HAZARD_CLASSES = {"rubble", "debris_heavy", "debris_light", "debris_moderate"}
CIVILIAN_CLASSES = {"civilian_visible", "group_of_civilians"}
RESCUE_CLASSES = {"rescue_team"}
BLOCKED_CLASSES = {"entry_door_blocked", "entry_window_blocked"}

CONF_ENV_DEFAULT = 0.35
```

## Interfaz — RescueDetector

```python
class RescueDetector:
    def __init__(self, model_path=MODELO_DRESPNET, device=None): ...

    def process(self, infer_frame, conf_env=0.35):
        # NO dibuja in-place (modelo de segmentacion)
        # Retorna objeto `result` de ultralytics o None
        # Para dibujar: result.plot(img=canvas)

    def extract_access(self, result, conf_env=0.35) -> list[tuple[str, list]]:
        # Retorna [(nombre, [x1,y1,x2,y2]), ...] solo ACCESS_CLASSES
        # Filtra por conf_env: descarta cajas con conf < conf_env ANTES
        # de chequear la clase (mismo filtro que extract_hazards()).
        # Implementacion real:
        #   for b in result.boxes:
        #       if float(b.conf[0]) < conf_env: continue
        #       name = names.get(int(b.cls[0]), str(int(b.cls[0])))
        #       if name in ACCESS_CLASSES: out.append((name, [x1,y1,x2,y2]))

    def extract_hazards(self, result, conf_env=0.35) -> dict:
        # Retorna:
        # {
        #   "hazards": [(name, box, conf), ...],      # rubble/debris
        #   "civilians": [(name, box, conf), ...],     # civilian_visible/group
        #   "rescue_teams": [(name, box, conf), ...],  # rescue_team
        #   "blocked": [(name, box, conf), ...],       # door/window blocked
        # }

    def count_detections(self, result) -> int:
        # Total de detecciones (todas las clases), SIN filtrar por conf_env.
        # Implementacion real (una linea):
        #   return 0 if (result is None or result.boxes is None) else len(result.boxes)
```

### Uso de extract_access() vs extract_hazards()

`extract_access()` devuelve solo accesos transitables (para rutas de rescate).
`extract_hazards()` devuelve las 8 clases restantes agrupadas por tipo.
Ambos metodos operan sobre el mismo `result` — se llaman uno despues del otro.

## Como se Usa en el Orquestador

```python
# Cada N frames:
result = rescue_detector.process(infer_frame, conf_env=args.conf_env)
frame[:] = result.plot(img=frame)  # dibujar mascaras/cajas

# Cada frame (reusa last_env_result):
accesses = rescue_detector.extract_access(result)
env_info = rescue_detector.extract_hazards(result)
hazards = env_info["hazards"]       # → fusion con EPP bodyparts
civilians = env_info["civilians"]   # → labels de civil detectado
rescue_teams = env_info["rescue_teams"]  # → contador en HUD
blocked = env_info["blocked"]       # → draw_blocked_access()
```

La fusion cruzada con EPP (`classify_rubble_victims()`) esta en
`ukucha_detector.py`, NO en este modulo.

## Costo Computacional

Es el detector MAS CARO (segmentacion + mascaras). En el pipeline unificado
se corre cada `--env-every` frames (default 5). Fall y EPP corren cada frame.

VRAM estimada: ~45MB (yolov8s-seg es mediano).

## Standalone

```bash
venv\Scripts\python.exe detectors/rescue_detector.py
```

Abre webcam, muestra detecciones de entorno con mascaras. Imprime advertencia
de domain shift al iniciar. Tecla 'q' para salir.

### Comportamiento exacto del bloque `__main__`

1. Imprime `"Cargando RescueDetector (DRespNeT best.pt)..."` y crea
   `RescueDetector()`.
2. Abre `cv2.VideoCapture(0)`; si `not cap.isOpened()`, imprime
   `"ERROR: no se pudo abrir la camara."` y retorna sin entrar al loop.
3. Imprime el warning de domain shift (texto EXACTO, dos lineas):
   ```
   ADVERTENCIA: modelo entrenado con imagenes aereas (dron).
   Con camara terrestre la deteccion sera menos confiable (domain shift).
   ```
4. Imprime `"Presiona 'q' para salir."`.
5. Loop principal (dentro de `try/finally` que libera la camara y cierra
   ventanas al salir):
   - Lee frame con `cap.read()`; si `not ret`, rompe el loop.
   - Llama `detector.process(frame)` → `result`.
   - `annotated = result.plot() if result is not None else frame` (usa
     `result.plot()` SIN `img=` aqui, a diferencia del uso en el orquestador
     que pasa `img=canvas`; el standalone genera su propio frame anotado).
   - Calcula FPS instantaneo: `1.0 / max(now - prev_time, 1e-6)`.
   - `n = detector.count_detections(result)`.
   - Dibuja overlay en amarillo `(0, 255, 255)` en `(10, 30)` con
     `cv2.FONT_HERSHEY_SIMPLEX` escala 0.6, texto:
     `"FPS: {fps:.1f}  Detecciones entorno: {n}"`.
   - Muestra la ventana `"Rescue Detector / DRespNeT (standalone)"` con
     `cv2.imshow`.
   - Sale del loop si `cv2.waitKey(1) & 0xFF == ord('q')`.
6. En el `finally`: `cap.release()` + `cv2.destroyAllWindows()`.

## Bugs a Evitar

- **NO usar `track()` aqui** — el entorno no se mueve, `predict()` simple es
  suficiente y mas eficiente.
- **NO correr cada frame** — segmentacion es costosa, respetar `env_every`.
- **NO usar clases `*_blocked` como destino de ruta de rescate** — solo las
  `*_accessible` son transitables.
- **Domain shift es REAL** — el modelo fue entrenado con vistas aereas. Con
  camara terrestre/indoor, las cortinas pueden confundirse con accesos
  bloqueados, objetos grandes con rubble, etc. Confianza baja es esperada.

## Verificacion

1. `python detectors/rescue_detector.py` → webcam abre, advertencia de domain shift
2. Sobre imagenes aereas de escombros: produce detecciones (aunque baja confianza)
3. No crashea con `result=None` (frame sin detecciones)
4. `extract_hazards()` devuelve dict con las 4 listas (pueden estar vacias)
5. `extract_access()` solo devuelve ACCESS_CLASSES (no blocked)

## Referencias

- Script original: `run_ukucha_dual.py` (funcion `extract_access`) del repo
  del compañero (Anderbstz/data)
- DRespNeT paper: https://arxiv.org/abs/2508.16016
- Skills relacionadas: `ukucha/epp-detector.md`, `ukucha/fall-detector.md`
