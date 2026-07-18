"""
ukucha_detector.py — Pipeline unificado UKUCHA: 1 camara, 3 detectores.

Combina en un solo frame:
  1. FallDetector   (detectors/fall_detector.py)  — caidas / posturas (YOLOv8n + MediaPipe Pose)
  2. EppDetector     (detectors/epp_detector.py)   — EPP + victima/rescatista (yolo8m.pt, SH17)
  3. RescueDetector  (detectors/rescue_detector.py) — entorno/escombros/accesos (DRespNeT best.pt)

Cada detector es independiente y standalone (ver su propio __main__).
Este archivo es la capa de orquestacion + fusion (ruta de rescate
victima -> acceso transitable mas cercano).

Optimizacion de costo GPU: DRespNeT (segmentacion, el mas caro) se corre
cada --env-every frames; fall + EPP corren cada frame.

Uso:
    venv\\Scripts\\python.exe ukucha_detector.py
    venv\\Scripts\\python.exe ukucha_detector.py --cam 1 --env-every 3
Salir: 'q'.
"""
import argparse
import csv
import queue
import threading
import time
from datetime import datetime
from math import hypot
from pathlib import Path

import cv2
import requests

from detectors.fall_detector import FallDetector
from detectors.epp_detector import EppDetector, CONF_VICTIM_DEFAULT, CONF_EPP_DEFAULT
from detectors.rescue_detector import RescueDetector, CONF_ENV_DEFAULT

COL_ROUTE = (0, 255, 255)
COL_RUBBLE_VICTIM = (180, 0, 180)  # magenta — persona bajo escombros
COL_RUBBLE_ZONE = (0, 140, 140)    # teal — zona de escombros sin persona
COL_BLOCKED = (0, 0, 180)          # rojo oscuro — acceso bloqueado
COL_CIVILIAN = (200, 100, 0)       # azul-naranja — civil detectado por DRespNeT
COL_INDICIO = (0, 165, 255)        # ambar — indicios de persona (bodyparts aisladas)

BODYPART_ES = {
    "head": "cabeza",
    "face": "rostro",
    "hands": "manos",
    "foot": "pie",
}

# Evidencia de victimas confirmadas (snapshot + registro CSV)
DET_DIR = Path(__file__).resolve().parent / "outputs" / "detections"
CONFIRM_FRAMES = 3  # frames que una victima debe persistir para registrarse
DEDUP_IOU = 0.3     # IoU minimo para considerar que dos bboxes son la misma persona


class ServerNotifier:
    """
    Envia eventos de deteccion a server.py (POST /api/deteccion) sin
    bloquear el loop de video. Corre en un hilo daemon aparte con una cola
    acotada (maxsize=20): si el server esta caido, lento, o no esta
    corriendo, los eventos simplemente se descartan — NUNCA se traba ni
    se propaga una excepcion hacia el loop principal de captura/deteccion.
    Deshabilitado por defecto (opt-in via --server-url).
    """

    def __init__(self, base_url, timeout=1.5):
        self.enabled = bool(base_url)
        self.timeout = timeout
        self._warned = False
        if self.enabled:
            self.url = f"{base_url.rstrip('/')}/api/deteccion"
            self._q = queue.Queue(maxsize=20)
            self._thread = threading.Thread(target=self._worker, daemon=True)
            self._thread.start()

    def send(self, event: dict):
        if not self.enabled:
            return
        try:
            self._q.put_nowait(event)
        except queue.Full:
            pass  # server lento: se descarta el evento, no se acumula lag

    def _worker(self):
        while True:
            event = self._q.get()
            try:
                requests.post(self.url, json=event, timeout=self.timeout)
            except requests.exceptions.RequestException as e:
                if not self._warned:
                    print(f"[server] No se pudo enviar evento a {self.url}: {e}")
                    print("[server] (¿server.py no esta corriendo? se silencian avisos futuros)")
                    self._warned = True


class WebcamStream:
    """Captura en hilo aparte para eliminar el lag."""

    def __init__(self, src=0):
        self.cap = cv2.VideoCapture(src)
        if not self.cap.isOpened():
            print(f"Error: No se pudo acceder a la camara con indice: {src}")
            self.running = False
            return
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.ret, self.frame = self.cap.read()
        self._lock = threading.Lock()
        self.running = True
        self.thread = threading.Thread(target=self.update, args=())
        self.thread.daemon = True
        self.thread.start()

    def update(self):
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                with self._lock:
                    self.ret = ret
                    self.frame = frame
            time.sleep(0.005)

    def read(self):
        with self._lock:
            if self.frame is None:
                return False, None
            return self.ret, self.frame.copy()

    def stop(self):
        self.running = False
        self.cap.release()


def pick_device():
    try:
        import torch
        return 0 if torch.cuda.is_available() else "cpu"
    except Exception:
        return "cpu"


def _center(xyxy):
    x1, y1, x2, y2 = xyxy
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


def _iou(a, b):
    x1 = max(a[0], b[0]); y1 = max(a[1], b[1])
    x2 = min(a[2], b[2]); y2 = min(a[3], b[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def _inside_box(pt, box):
    return box[0] <= pt[0] <= box[2] and box[1] <= pt[1] <= box[3]


def _same_person(a, b):
    """
    Heuristica tolerante para decidir si dos bboxes son la MISMA persona
    entre confirmaciones. Solo IoU falla cuando la persona se mueve o
    gesticula (el bbox cambia de tamano/forma sin ser alguien distinto),
    asi que se combina con distancia de centros relativa al tamano del
    bbox: si los centros estan cerca (medio bbox de distancia), es la
    misma persona aunque el IoU haya caido por debajo del umbral.
    """
    if _iou(a, b) >= DEDUP_IOU:
        return True
    ca, cb = _center(a), _center(b)
    dist = hypot(ca[0] - cb[0], ca[1] - cb[1])
    diag_a = hypot(a[2] - a[0], a[3] - a[1])
    diag_b = hypot(b[2] - b[0], b[3] - b[1])
    avg_diag = (diag_a + diag_b) / 2.0
    return dist <= 0.5 * avg_diag


def link_victims_access(frame, victims, accesses, max_dist):
    """Dibuja la ruta de rescate desde cada victima al acceso transitable mas cercano."""
    n_links = 0
    for _, vbox, _ in victims:
        vc = _center(vbox)
        best, best_d = None, 1e12
        for _, abox in accesses:
            ac = _center(abox)
            if _inside_box(ac, vbox):
                continue
            d = hypot(vc[0] - ac[0], vc[1] - ac[1])
            if d < best_d:
                best_d, best = d, abox
        if best is not None and best_d <= max_dist:
            ac = _center(best)
            cv2.line(frame, (int(vc[0]), int(vc[1])), (int(ac[0]), int(ac[1])), COL_ROUTE, 2)
            cv2.putText(frame, "RUTA DE RESCATE",
                        (int((vc[0] + ac[0]) / 2) - 60, int((vc[1] + ac[1]) / 2)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, COL_ROUTE, 2)
            n_links += 1
    return n_links


def _overlaps(box_a, box_b):
    """True if center of box_a is inside box_b or IoU > 0.1."""
    ca = _center(box_a)
    if _inside_box(ca, box_b):
        return True
    return _iou(box_a, box_b) > 0.1


def classify_rubble_victims(frame, bodyparts, hazards, civilians, victims,
                            fall_personas):
    """
    Cross-correlate EPP detections with DRespNeT hazards to classify:
      - PERSONA BAJO ESCOMBROS: bodypart overlapping rubble/debris
      - VICTIMA EN ESCOMBROS: full victim overlapping rubble/debris
      - CIVIL DETECTADO: civilian_visible from DRespNeT
      - CAIDA EN ESCOMBROS: fallen person overlapping rubble
      - ZONA DE ESCOMBROS: rubble/debris with no person nearby
    Returns dict with rubble_victims list and counts.
    """
    rubble_victims = []
    matched_hazards = set()

    for tid, name, bpbox in bodyparts:
        for hi, (hname, hbox, hconf) in enumerate(hazards):
            if _overlaps(bpbox, hbox):
                matched_hazards.add(hi)
                name_es = BODYPART_ES.get(name, name)
                label = f"BAJO ESCOMBROS ({name_es})"
                x1, y1, x2, y2 = map(int, bpbox)
                cv2.rectangle(frame, (x1 - 2, y1 - 2), (x2 + 2, y2 + 2),
                              COL_RUBBLE_VICTIM, 3)
                (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX,
                                              0.55, 2)
                cv2.rectangle(frame, (x1, y1 - th - 10), (x1 + tw, y1),
                              COL_RUBBLE_VICTIM, -1)
                cv2.putText(frame, label, (x1, y1 - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
                rubble_victims.append((bpbox, label))
                break

    for tid, vbox, confirmable in victims:
        if not confirmable:
            continue
        for hi, (hname, hbox, hconf) in enumerate(hazards):
            if _overlaps(vbox, hbox):
                matched_hazards.add(hi)
                label = "VICTIMA EN ESCOMBROS"
                x1, y1, x2, y2 = map(int, vbox)
                cv2.rectangle(frame, (x1 - 2, y1 - 2), (x2 + 2, y2 + 2),
                              COL_RUBBLE_VICTIM, 3)
                cv2.putText(frame, label, (x1, y2 + 18),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, COL_RUBBLE_VICTIM, 2)
                rubble_victims.append((vbox, label))
                break

    for cname, cbox, cconf in civilians:
        nice = cname.replace("_", " ").upper()
        label = f"{nice} ({cconf:.0%})"
        x1, y1, x2, y2 = map(int, cbox)
        cv2.rectangle(frame, (x1, y1), (x2, y2), COL_CIVILIAN, 2)
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(frame, (x1, y1 - th - 6), (x1 + tw + 4, y1),
                      COL_CIVILIAN, -1)
        cv2.putText(frame, label, (x1 + 2, y1 - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        for hi, (hname, hbox, hconf) in enumerate(hazards):
            if _overlaps(cbox, hbox):
                matched_hazards.add(hi)
                rubble_victims.append((cbox, "CIVIL BAJO ESCOMBROS"))
                cv2.putText(frame, "BAJO ESCOMBROS", (x1, y2 + 15),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, COL_RUBBLE_VICTIM, 2)
                break

    n_fall_rubble = 0
    for pinfo in fall_personas:
        pbox = pinfo["bbox"]
        if pinfo["estado"] not in ("EN EL SUELO", "CAYENDO"):
            continue
        for hi, (hname, hbox, hconf) in enumerate(hazards):
            if _overlaps(pbox, hbox):
                matched_hazards.add(hi)
                n_fall_rubble += 1
                x1, y1 = int(pbox[0]), int(pbox[1])
                cv2.putText(frame, "CAIDA EN ESCOMBROS", (x1, int(pbox[3]) + 35),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2)
                break

    n_risk_zones = 0
    for hi, (hname, hbox, hconf) in enumerate(hazards):
        if hi not in matched_hazards:
            n_risk_zones += 1
            x1, y2 = int(hbox[0]), int(hbox[3])
            nice = hname.replace("_", " ")
            cv2.putText(frame, f"ESCOMBROS: {nice}", (x1, y2 + 14),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, COL_RUBBLE_ZONE, 1)

    return {
        "rubble_victims": rubble_victims,
        "n_fall_rubble": n_fall_rubble,
        "n_risk_zones": n_risk_zones,
        "n_civilians": len(civilians),
    }


def draw_blocked_access(frame, blocked):
    """Draw X over blocked entry points."""
    for name, box, conf in blocked:
        x1, y1, x2, y2 = map(int, box)
        cv2.rectangle(frame, (x1, y1), (x2, y2), COL_BLOCKED, 2)
        cv2.line(frame, (x1, y1), (x2, y2), COL_BLOCKED, 2)
        cv2.line(frame, (x2, y1), (x1, y2), COL_BLOCKED, 2)
        nice = name.replace("_", " ")
        cv2.putText(frame, f"BLOQUEADO: {nice}", (x1, y1 - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, COL_BLOCKED, 1)


def banner(frame, text, y, color=(255, 255, 255)):
    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
    cv2.rectangle(frame, (5, y - th - 6), (15 + tw, y + 4), (0, 0, 0), -1)
    cv2.putText(frame, text, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cam", type=int, default=0)
    parser.add_argument("--conf-victim", type=float, default=CONF_VICTIM_DEFAULT)
    parser.add_argument("--conf-epp", type=float, default=CONF_EPP_DEFAULT)
    parser.add_argument("--conf-env", type=float, default=CONF_ENV_DEFAULT)
    parser.add_argument("--env-every", type=int, default=5,
                        help="correr DRespNeT 1 de cada N frames (mas alto = mas FPS)")
    parser.add_argument("--route-frac", type=float, default=0.35,
                        help="distancia max victima-acceso, como fraccion de la diagonal")
    parser.add_argument("--show-all-epp", action="store_true")
    parser.add_argument("--no-fall", action="store_true", help="desactivar capa de caidas")
    parser.add_argument("--no-epp", action="store_true", help="desactivar capa de EPP")
    parser.add_argument("--no-rescue", action="store_true", help="desactivar capa de entorno/escombros")
    parser.add_argument("--server-url", type=str, default=None,
                        help="URL base de server.py (ej: http://localhost:8000) para enviar "
                             "eventos de deteccion. Si se omite, no se envia nada (default).")
    args = parser.parse_args()

    args.conf_victim = max(0.0, min(1.0, args.conf_victim))
    args.conf_epp = max(0.0, min(1.0, args.conf_epp))
    args.conf_env = max(0.0, min(1.0, args.conf_env))
    args.route_frac = max(0.0, min(1.0, args.route_frac))
    args.env_every = max(1, args.env_every)

    if args.no_fall and args.no_epp and args.no_rescue:
        print("ADVERTENCIA: todos los detectores estan desactivados "
              "(--no-fall --no-epp --no-rescue). Solo se mostrara la camara.")

    device = pick_device()
    print(f"Dispositivo: {'cuda:0' if device == 0 else device}")

    models_dir = Path(__file__).resolve().parent / "models"
    required_models = []
    if not args.no_fall:
        required_models.append(("yolov8n.pt", "fall detector"))
    if not args.no_epp:
        required_models.append(("epp_yolo8m.pt", "EPP detector"))
    if not args.no_rescue:
        required_models.append(("drespnet_best.pt", "rescue detector"))
    for fname, desc in required_models:
        if not (models_dir / fname).exists():
            print(f"ERROR: no se encontro models/{fname} (requerido por {desc}).")
            print(f"  Colocar el archivo en: {models_dir / fname}")
            return

    notifier = ServerNotifier(args.server_url)
    if notifier.enabled:
        print(f"Eventos de deteccion -> {notifier.url}")

    DET_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = DET_DIR / "detections_log.csv"
    if not csv_path.exists():
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(["timestamp", "victim_id", "snapshot"])

    fall_detector = None if args.no_fall else FallDetector(device=device)
    epp_detector = None if args.no_epp else EppDetector(device=device)
    rescue_detector = None if args.no_rescue else RescueDetector(device=device)

    cam = WebcamStream(src=args.cam)
    if not cam.running:
        return

    window_name = "UKUCHA - Deteccion Integral (caidas + EPP + rescate)"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, 1280, 720)

    prev_time = time.time()
    frame_idx = 0
    last_env_result = None
    victim_seen = {}    # track_id (EPP) -> frames consecutivos visto
    logged_ids = set()  # track_id ya registrados con snapshot+CSV
    logged_boxes = {}   # track_id -> ultimo bbox conocido (para dedup espacial)
    victim_last_frame = {}  # track_id -> ultimo frame_idx donde se vio
    PRUNE_INTERVAL = 300    # podar cada N frames (~10s a 30fps)
    PRUNE_STALE = 900       # borrar IDs no vistos en N frames (~30s)
    prev_alerta_caida = False
    prev_critica_caida = False
    prev_rubble_victims = 0

    print("\nListo. Presiona 'q' para salir.")
    print(f"Evidencia -> {DET_DIR}")

    try:
        while True:
            ret, frame = cam.read()
            if not ret or frame is None:
                time.sleep(0.01)
                continue
            frame_idx += 1
            h, w = frame.shape[:2]
            diag = hypot(w, h)
            now = time.monotonic()

            # Copia LIMPIA del frame de camara: se usa SOLO para inferencia en
            # los 3 modelos. 'frame' es el canvas que acumula las anotaciones
            # y es lo que finalmente se muestra. Si se infiere sobre un frame
            # ya dibujado (cajas/texto de un detector anterior), el modelo
            # siguiente interpreta esos pixeles como si fueran parte real de
            # la escena — degrada deteccion en cadena. Por eso cada detector
            # recibe infer_frame para inferir y frame (canvas) para dibujar.
            infer_frame = frame.copy()

            hay_alerta_caida = False
            hay_critica_caida = False
            victims, n_rescuer, n_epp = [], 0, 0
            bodyparts = []
            accesses = []
            hazards, civilians, rescue_teams, blocked = [], [], [], []
            n_env = 0
            fall_personas = []

            # 1) Caidas — infiere sobre infer_frame, dibuja sobre frame (canvas)
            if fall_detector is not None:
                info_fall = fall_detector.process(infer_frame, now, mostrar_landmarks=True,
                                                   device=device, canvas=frame)
                hay_alerta_caida = info_fall["hay_alerta"]
                hay_critica_caida = info_fall["hay_critica"]
                fall_personas = info_fall.get("personas", [])

            # 2) Entorno/escombros (DRespNeT) — infiere sobre infer_frame,
            #    cada N frames (el mas costoso); fusiona sobre frame (canvas)
            #
            # IMPORTANTE: el overlay (plot) solo se dibuja en el MISMO frame
            # donde se acaba de recalcular. Si se reusaran las cajas de
            # last_env_result sobre el frame actual en frames "salteados",
            # quedarian dibujadas en la posicion de hace N frames — si la
            # camara o la escena se movio, se ve una caja de "escombro" o
            # "acceso" en un lugar donde ya no hay nada, engañoso para un
            # sistema de seguridad. Las posiciones (accesses/n_env) para la
            # logica de ruta de rescate SI se reusan entre recalculos (el
            # entorno fisico no cambia tan rapido), solo el DIBUJO no.
            if rescue_detector is not None:
                recompute_env = (args.env_every <= 1
                                 or frame_idx % args.env_every == 0
                                 or last_env_result is None)
                if recompute_env:
                    last_env_result = rescue_detector.process(infer_frame, conf_env=args.conf_env)
                    if last_env_result is not None:
                        frame[:] = last_env_result.plot(img=frame)
                if last_env_result is not None:
                    accesses = rescue_detector.extract_access(last_env_result, conf_env=args.conf_env)
                    env_info = rescue_detector.extract_hazards(last_env_result, conf_env=args.conf_env)
                    hazards = env_info["hazards"]
                    civilians = env_info["civilians"]
                    rescue_teams = env_info["rescue_teams"]
                    blocked = env_info["blocked"]
                    n_env = rescue_detector.count_detections(last_env_result)

            # 3) EPP + victima/rescatista — infiere sobre infer_frame, dibuja sobre frame (canvas)
            if epp_detector is not None:
                info_epp = epp_detector.process(
                    infer_frame, conf_victim=args.conf_victim, conf_epp=args.conf_epp,
                    show_all_epp=args.show_all_epp, canvas=frame,
                )
                victims = info_epp["victims"]
                n_rescuer = info_epp["n_rescuer"]
                n_epp = info_epp["n_epp"]
                bodyparts = info_epp.get("bodyparts", [])

            # Fusion: ruta de rescate victima -> acceso transitable
            n_routes = 0
            if victims and accesses:
                n_routes = link_victims_access(frame, victims, accesses, args.route_frac * diag)

            # Fusion: EPP x DRespNeT — clasificar escenarios de escombros
            fusion = {"rubble_victims": [], "n_fall_rubble": 0,
                      "n_risk_zones": 0, "n_civilians": 0}
            if hazards or civilians:
                fusion = classify_rubble_victims(
                    frame, bodyparts, hazards, civilians, victims, fall_personas)

            if blocked:
                draw_blocked_access(frame, blocked)

            # EVIDENCIA: confirmar y registrar victimas nuevas (requiere track_id
            # del EPP detector; victimas sin id estable -detecciones sueltas de
            # una sola vez- no se confirman para evitar falsos positivos).
            # Solo persona completa (confirmable=True): partes de cuerpo aisladas
            # (cabeza/mano sueltas por oclusion momentanea) NO generan evidencia,
            # solo se muestran visualmente — casi siempre es la MISMA persona ya
            # confirmada, vista parcialmente.
            for tid, vbox, confirmable in victims:
                if tid is None or not confirmable:
                    continue
                victim_seen[tid] = victim_seen.get(tid, 0) + 1
                victim_last_frame[tid] = frame_idx
                if victim_seen[tid] == CONFIRM_FRAMES and tid not in logged_ids:
                    already = any(_same_person(vbox, lb) for lb in logged_boxes.values())
                    if already:
                        logged_ids.add(tid)
                        continue
                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                    snap = DET_DIR / f"victima_{tid}_{ts}.jpg"
                    if not cv2.imwrite(str(snap), frame):
                        print(f"[EVIDENCIA] ADVERTENCIA: no se pudo guardar {snap.name}")
                    with open(csv_path, "a", newline="", encoding="utf-8") as f:
                        csv.writer(f).writerow([ts, tid, snap.name])
                    logged_ids.add(tid)
                    logged_boxes[tid] = vbox
                    print(f"[EVIDENCIA] Victima #{tid} confirmada -> {snap.name}")
                    notifier.send({"tipo": "victima_confirmada", "victim_id": tid,
                                   "snapshot": snap.name})
                elif tid in logged_boxes:
                    logged_boxes[tid] = vbox

            # Notificar al server SOLO en transiciones (borde de subida), no
            # cada frame — evita spam si el estado se mantiene por segundos
            if hay_critica_caida and not prev_critica_caida:
                notifier.send({"tipo": "caida_critica",
                               "detalle": "persona en el suelo por tiempo prolongado"})
            elif hay_alerta_caida and not prev_alerta_caida:
                notifier.send({"tipo": "caida_detectada"})
            prev_alerta_caida, prev_critica_caida = hay_alerta_caida, hay_critica_caida

            n_rubble_now = len(fusion["rubble_victims"])
            if n_rubble_now > 0 and prev_rubble_victims == 0:
                for rv_box, rv_label in fusion["rubble_victims"]:
                    notifier.send({"tipo": "persona_bajo_escombros",
                                   "detalle": rv_label})
            if fusion["n_fall_rubble"] > 0 and prev_rubble_victims == 0:
                notifier.send({"tipo": "caida_en_escombros",
                               "detalle": f"{fusion['n_fall_rubble']} persona(s) caida(s) en zona de escombros"})
            prev_rubble_victims = n_rubble_now

            if frame_idx % PRUNE_INTERVAL == 0:
                stale = [t for t, f in victim_last_frame.items()
                         if frame_idx - f > PRUNE_STALE and t not in logged_ids]
                for t in stale:
                    victim_seen.pop(t, None)
                    victim_last_frame.pop(t, None)

            # HUD
            now_wall = time.time()
            fps = 1.0 / max(now_wall - prev_time, 1e-6)
            prev_time = now_wall
            banner(frame, f"FPS: {fps:.1f}", 28, (0, 255, 0))
            if epp_detector is not None:
                banner(frame, f"VICTIMAS: {len(victims)} (unicas conf.: {len(logged_ids)})  "
                              f"RESCATISTAS: {n_rescuer}  EPP: {n_epp}",
                       56, (0, 0, 255) if victims else (200, 200, 200))
            if rescue_detector is not None:
                env_parts = [f"ENTORNO: {n_env}", f"RUTAS: {n_routes}"]
                if fusion["rubble_victims"]:
                    env_parts.append(f"BAJO ESCOMBROS: {len(fusion['rubble_victims'])}")
                if fusion["n_risk_zones"]:
                    env_parts.append(f"ZONAS RIESGO: {fusion['n_risk_zones']}")
                if fusion["n_civilians"]:
                    env_parts.append(f"CIVILES: {fusion['n_civilians']}")
                if rescue_teams:
                    env_parts.append(f"EQ.RESCATE: {len(rescue_teams)}")
                if blocked:
                    env_parts.append(f"BLOQUEADOS: {len(blocked)}")
                env_color = COL_RUBBLE_VICTIM if fusion["rubble_victims"] else (
                    COL_ROUTE if n_routes else (200, 200, 200))
                banner(frame, "  ".join(env_parts), 84, env_color)

            if bodyparts:
                partes_unicas = sorted(set(
                    BODYPART_ES.get(nm, nm) for _, nm, _ in bodyparts
                ))
                if len(partes_unicas) == 1:
                    detalle = partes_unicas[0]
                else:
                    detalle = ", ".join(partes_unicas[:-1]) + " y " + partes_unicas[-1]
                banner(frame,
                       f"INDICIO DE PERSONA - {detalle} detectada(s)",
                       112, COL_INDICIO)

            if hay_critica_caida:
                blink = int(now * 4) % 2 == 0
                if blink:
                    cv2.putText(frame, "!! EMERGENCIA !!", (30, h - 90),
                                cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)
                    cv2.putText(frame, "PERSONA EN EL SUELO", (30, h - 55),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            elif hay_alerta_caida:
                cv2.putText(frame, "!! CAIDA DETECTADA !!", (30, h - 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 3)

            if fusion["rubble_victims"]:
                blink_r = int(now * 3) % 2 == 0
                if blink_r:
                    y_rb = h - 130 if hay_critica_caida else (h - 95 if hay_alerta_caida else h - 60)
                    cv2.putText(frame, "!! PERSONA BAJO ESCOMBROS !!", (30, y_rb),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, COL_RUBBLE_VICTIM, 3)

            cv2.putText(frame, "UKUCHA | 'q' salir", (10, h - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

            cv2.imshow(window_name, frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    except KeyboardInterrupt:
        print("\nInterrumpido manualmente.")
    finally:
        print("Liberando recursos...")
        cam.stop()
        if fall_detector is not None:
            fall_detector.close()
        cv2.destroyAllWindows()
        print("Finalizado.")


if __name__ == "__main__":
    main()
