"""
UKUCHA Fall Detector — Deteccion de caidas en tiempo real.

Sistema de 5 senales ponderadas con soporte de cuerpo parcial:
  1. Angulo 3D del torso (world landmarks)
  2. Ratio de extension de piernas (3D)
  3. Compactacion vertical de keypoints (2D)
  4. Angulo 2D cabeza-tobillos
  5. Aspect ratio del bounding box

Tracking por IoU entre frames, 5 estados de postura,
deteccion de transicion temporal, y alerta escalada.
"""
import os
import sys

os.environ["LC_ALL"] = "en_US.UTF-8"

import math
import time
import cv2
import numpy as np
from collections import deque
from ultralytics import YOLO
import mediapipe as mp

# ──────────────────────────────────────────────
# CONFIGURACION
# ──────────────────────────────────────────────
FUENTE_VIDEO = 0
VENTANA_ANCHO = 1280
VENTANA_ALTO = 720
MOSTRAR_LANDMARKS = True
MODELO_YOLO = "yolov8n.pt"
MIN_VISIBILIDAD = 0.5
MIN_VISIBILIDAD_PARCIAL = 0.3
MIN_ALTO_BBOX = 60
MIN_KEYPOINTS_PARCIAL = 3
MIN_CONFIANZA_YOLO = 0.40

UMBRAL_SCORE_CAIDO = 0.40
UMBRAL_SCORE_CAYENDO = 0.25

DELTA_CAYENDO = 0.12
FRAMES_CONFIRMAR = 6

SEGUNDOS_ALERTA_CRITICA = 5

IOU_MIN_MATCH = 0.15
SCORE_SMOOTH_FRAMES = 3
MAX_FRAMES_SIN_POSE = 5
MIN_ASPECT_HUMANO = 0.20
# ──────────────────────────────────────────────

print("Cargando modelo YOLO...")
model = YOLO(MODELO_YOLO)
print("YOLO cargado OK.")

mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils
LM = mp_pose.PoseLandmark

_TORSO_LM = [LM.LEFT_SHOULDER, LM.RIGHT_SHOULDER, LM.LEFT_HIP, LM.RIGHT_HIP]
_SHOULDER_LM = [LM.LEFT_SHOULDER, LM.RIGHT_SHOULDER]
_HIP_LM = [LM.LEFT_HIP, LM.RIGHT_HIP]
_KNEE_LM = [LM.LEFT_KNEE, LM.RIGHT_KNEE]
_ANKLE_LM = [LM.LEFT_ANKLE, LM.RIGHT_ANKLE]

_ALL_BODY_LM = [
    LM.NOSE,
    LM.LEFT_SHOULDER, LM.RIGHT_SHOULDER,
    LM.LEFT_ELBOW, LM.RIGHT_ELBOW,
    LM.LEFT_WRIST, LM.RIGHT_WRIST,
    LM.LEFT_HIP, LM.RIGHT_HIP,
    LM.LEFT_KNEE, LM.RIGHT_KNEE,
    LM.LEFT_ANKLE, LM.RIGHT_ANKLE,
]

COLORES = {
    "DE PIE":        (0, 200, 0),
    "SENTADO":       (0, 200, 200),
    "CAYENDO":       (0, 165, 255),
    "EN EL SUELO":   (0, 0, 255),
    "RECUPERANDOSE": (255, 165, 0),
    "PARCIAL":       (200, 200, 0),
}


# ── Utilidades ──

def _vis(landmarks, punto):
    return landmarks[punto.value].visibility > MIN_VISIBILIDAD


def _vis_parcial(landmarks, punto):
    return landmarks[punto.value].visibility > MIN_VISIBILIDAD_PARCIAL


def _normalizar(valor, bajo, alto):
    if valor <= bajo:
        return 0.0
    if valor >= alto:
        return 1.0
    return (valor - bajo) / (alto - bajo)


def _angulo_3d_vs_vertical(vec):
    vertical = np.array([0.0, 1.0, 0.0])
    norm = np.linalg.norm(vec)
    if norm < 1e-6:
        return 0.0
    cos_a = np.dot(vec, vertical) / norm
    return np.degrees(np.arccos(np.clip(cos_a, -1.0, 1.0)))


def _angulo_2d(punto_bajo, punto_alto):
    dy = punto_bajo[1] - punto_alto[1]
    dx = punto_bajo[0] - punto_alto[0]
    return abs(90 - np.degrees(math.atan2(dy, dx)))


def _promedio_3d(wl, puntos):
    coords = np.array([[wl[p.value].x, wl[p.value].y, wl[p.value].z] for p in puntos])
    return coords.mean(axis=0)


def _calcular_iou(box_a, box_b):
    x1 = max(box_a[0], box_b[0])
    y1 = max(box_a[1], box_b[1])
    x2 = min(box_a[2], box_b[2])
    y2 = min(box_a[3], box_b[3])
    inter = max(0, x2 - x1) * max(0, y2 - y1)
    area_a = (box_a[2] - box_a[0]) * (box_a[3] - box_a[1])
    area_b = (box_b[2] - box_b[0]) * (box_b[3] - box_b[1])
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def _landmark_en_frame(lm_entry):
    """Verifica que el landmark este dentro del frame (no hallucinado en bordes)."""
    return 0.05 < lm_entry.x < 0.95 and 0.05 < lm_entry.y < 0.95


def evaluar_visibilidad(landmarks, alto_box, ancho_box, frame_h, frame_w):
    """
    Evalua que tan visible es el cuerpo.
    Retorna: 'completo', 'parcial', 'muy_cerca', o 'insuficiente'.
    """
    # Si el bbox cubre >70% del frame, la persona esta demasiado cerca
    cobertura = (alto_box * ancho_box) / max(frame_h * frame_w, 1)
    if cobertura > 0.70:
        return 'muy_cerca'

    hombros = sum(
        1 for p in _SHOULDER_LM
        if _vis(landmarks, p) and _landmark_en_frame(landmarks[p.value])
    )
    caderas = sum(
        1 for p in _HIP_LM
        if _vis(landmarks, p) and _landmark_en_frame(landmarks[p.value])
    )

    if hombros >= 1 and caderas >= 1:
        return 'completo'

    # Contar body landmarks que esten realmente en frame
    body_below_nose = [
        LM.LEFT_SHOULDER, LM.RIGHT_SHOULDER,
        LM.LEFT_ELBOW, LM.RIGHT_ELBOW,
        LM.LEFT_HIP, LM.RIGHT_HIP,
    ]
    cuerpo_real = sum(
        1 for p in body_below_nose
        if _vis_parcial(landmarks, p) and _landmark_en_frame(landmarks[p.value])
    )

    if hombros >= 1 and cuerpo_real >= 2:
        return 'parcial'

    return 'insuficiente'


# ── Deteccion de postura sentada (separada del score de caida) ──

def detectar_sentado(landmarks, world_landmarks):
    """
    Detecta si la persona esta sentada independientemente del score de caida.
    Sentado = torso vertical + piernas no extendidas hacia abajo.
    """
    hombros_vis = [p for p in _SHOULDER_LM if _vis(landmarks, p)]
    caderas_vis = [p for p in _HIP_LM if _vis_parcial(landmarks, p)]

    if not (hombros_vis and caderas_vis):
        return False

    wl = world_landmarks
    hombro_3d = _promedio_3d(wl, hombros_vis)
    cadera_3d = _promedio_3d(wl, caderas_vis)
    torso_vec = cadera_3d - hombro_3d
    angulo = _angulo_3d_vs_vertical(torso_vec)

    if angulo > 30:
        return False

    rodillas_vis = [p for p in _KNEE_LM if _vis(landmarks, p)]
    if not rodillas_vis:
        # Sin rodillas visibles, si torso vertical y caderas visibles
        # probablemente sentado (las piernas estan ocultas/dobladas)
        hombro_y = sum(landmarks[p.value].y for p in hombros_vis) / len(hombros_vis)
        cadera_y = sum(landmarks[p.value].y for p in caderas_vis) / len(caderas_vis)
        dist_torso = abs(cadera_y - hombro_y)
        # Si el torso ocupa mucha proporcion vertical del bbox, piernas estan dobladas
        return dist_torso > 0.3

    # Piernas visibles: verificar que NO esten extendidas verticalmente (de pie)
    rodilla_3d = _promedio_3d(wl, rodillas_vis)
    caida_pierna = rodilla_3d[1] - cadera_3d[1]
    torso_h = abs(cadera_3d[1] - hombro_3d[1])
    ratio = caida_pierna / max(torso_h, 0.01)

    # ratio < 0.5 = piernas no totalmente extendidas = sentado
    return ratio < 0.5


# ── Scoring multi-senal ──

def calcular_score_caida(landmarks, world_landmarks, w_p, h_p, alto_box, ancho_box,
                         modo_visibilidad='completo'):
    wl = world_landmarks
    signals = {}
    weights = {}

    hombros_vis = [p for p in _SHOULDER_LM if _vis(landmarks, p)]
    caderas_vis = [p for p in _HIP_LM if _vis_parcial(landmarks, p)]

    # Senal 1: Angulo 3D del torso
    angulo_torso_3d = None
    if hombros_vis and caderas_vis:
        hombro_3d = _promedio_3d(wl, hombros_vis)
        cadera_3d = _promedio_3d(wl, caderas_vis)
        torso_vec = cadera_3d - hombro_3d
        angulo_torso_3d = _angulo_3d_vs_vertical(torso_vec)
        signals['torso3d'] = _normalizar(angulo_torso_3d, 25, 55)
        weights['torso3d'] = 0.35

    # Senal 2: Ratio de extension de piernas (3D)
    ratio_pierna = None
    rodillas_vis = [p for p in _KNEE_LM if _vis(landmarks, p)]
    if rodillas_vis and caderas_vis:
        rodilla_3d = _promedio_3d(wl, rodillas_vis)
        cadera_3d_leg = _promedio_3d(wl, caderas_vis)
        if hombros_vis:
            hombro_3d_leg = _promedio_3d(wl, hombros_vis)
            torso_h = abs(cadera_3d_leg[1] - hombro_3d_leg[1])
        else:
            torso_h = 0.4
        caida_pierna = rodilla_3d[1] - cadera_3d_leg[1]
        ratio_pierna = caida_pierna / max(torso_h, 0.01)

        if ratio_pierna > 0.7:
            signals['piernas'] = 0.0
        elif ratio_pierna < 0.15:
            signals['piernas'] = 1.0
        else:
            signals['piernas'] = 1.0 - (ratio_pierna - 0.15) / (0.7 - 0.15)
        weights['piernas'] = 0.25

    # Senal 3: Compactacion vertical de keypoints (solo con 6+ landmarks)
    visibles = [
        p for p in _ALL_BODY_LM
        if _vis_parcial(landmarks, p) and _landmark_en_frame(landmarks[p.value])
    ]
    compactacion = None
    if len(visibles) >= 6:
        xs = [landmarks[p.value].x * w_p for p in visibles]
        ys = [landmarks[p.value].y * h_p for p in visibles]
        spread_x = max(xs) - min(xs)
        spread_y = max(ys) - min(ys)
        if spread_x > 10:
            compactacion = spread_y / spread_x

            if compactacion >= 1.5:
                signals['compact'] = 0.0
            elif compactacion <= 0.5:
                signals['compact'] = 1.0
            else:
                signals['compact'] = (1.5 - compactacion) / (1.5 - 0.5)
            weights['compact'] = 0.15

    # Senal 4: Angulo 2D cabeza-tobillos
    angulo_cuerpo_2d = None
    nariz = landmarks[LM.NOSE.value]
    tobillos_vis = [p for p in _ANKLE_LM if _vis(landmarks, p)]
    if nariz.visibility > MIN_VISIBILIDAD and tobillos_vis:
        coords_tobillos = [
            (landmarks[p.value].x * w_p, landmarks[p.value].y * h_p)
            for p in tobillos_vis
        ]
        tobillo_centro = (
            sum(c[0] for c in coords_tobillos) / len(coords_tobillos),
            sum(c[1] for c in coords_tobillos) / len(coords_tobillos),
        )
        cabeza = (nariz.x * w_p, nariz.y * h_p)
        angulo_cuerpo_2d = _angulo_2d(tobillo_centro, cabeza)
        signals['cuerpo2d'] = _normalizar(angulo_cuerpo_2d, 30, 60)
        weights['cuerpo2d'] = 0.15

    # Senal 5: Aspect ratio del bounding box (peso bajo — auxiliar)
    aspect = alto_box / max(ancho_box, 1)
    if aspect >= 1.3:
        signals['bbox'] = 0.0
    elif aspect <= 0.5:
        signals['bbox'] = 1.0
    else:
        signals['bbox'] = (1.3 - aspect) / (1.3 - 0.5)
    weights['bbox'] = 0.10

    if not weights:
        return 0.0, {'torso3d': None, 'piernas': None, 'compact': None,
                      'cuerpo2d': None, 'aspect': aspect, 'score': 0.0,
                      'modo': modo_visibilidad}

    total_peso = sum(weights.values())
    score = sum(signals[k] * weights[k] for k in signals) / total_peso

    sentado = detectar_sentado(landmarks, world_landmarks)

    debug = {
        'torso3d': angulo_torso_3d,
        'piernas': ratio_pierna,
        'compact': compactacion,
        'cuerpo2d': angulo_cuerpo_2d,
        'aspect': aspect,
        'score': score,
        'modo': modo_visibilidad,
        'n_signals': len(signals),
        'sentado': sentado,
    }
    return score, debug


# ── Estado de persona ──

class PersonState:
    HISTERESIS = 0.05

    def __init__(self, bbox):
        self.bbox = bbox
        self.scores_raw = deque(maxlen=SCORE_SMOOTH_FRAMES)
        self.estados = deque(maxlen=FRAMES_CONFIRMAR)
        self.score_smooth = 0.0
        self.score_prev = 0.0
        self.estado_actual = "DE PIE"
        self.tiempo_en_suelo = 0.0
        self.ts_ultimo_suelo = None

    def update(self, bbox, score_raw, now, sentado_geometrico=False):
        self.bbox = bbox
        self.scores_raw.append(score_raw)

        self.score_smooth = sum(self.scores_raw) / len(self.scores_raw)
        delta = self.score_smooth - self.score_prev
        self.score_prev = self.score_smooth

        estado_base = self._clasificar_base(self.score_smooth, sentado_geometrico)
        estado_final = self._aplicar_transicion(estado_base, delta, now)

        self.estados.append(estado_final)
        self.estado_actual = estado_final
        return estado_final

    def _clasificar_base(self, score, sentado_geometrico=False):
        prev = self.estado_actual
        if score >= UMBRAL_SCORE_CAIDO:
            return "EN EL SUELO"
        if prev == "EN EL SUELO" and score >= UMBRAL_SCORE_CAIDO - self.HISTERESIS:
            return "EN EL SUELO"
        if score >= UMBRAL_SCORE_CAYENDO:
            return "CAYENDO"
        # Deteccion geometrica de sentado (independiente del score)
        if sentado_geometrico:
            return "SENTADO"
        return "DE PIE"

    def _aplicar_transicion(self, estado_base, delta, now):
        prev = self.estado_actual

        if delta > DELTA_CAYENDO and prev in ("DE PIE", "SENTADO"):
            return "CAYENDO"

        if estado_base in ("EN EL SUELO", "SENTADO"):
            if prev == "EN EL SUELO" and delta < -DELTA_CAYENDO:
                self.ts_ultimo_suelo = None
                self.tiempo_en_suelo = 0.0
                return "RECUPERANDOSE"

            if estado_base == "EN EL SUELO":
                if self.ts_ultimo_suelo is None:
                    self.ts_ultimo_suelo = now
                self.tiempo_en_suelo = now - self.ts_ultimo_suelo
            return estado_base

        if estado_base == "DE PIE":
            if prev == "RECUPERANDOSE":
                avg = sum(self.scores_raw) / len(self.scores_raw)
                if avg < UMBRAL_SCORE_CAYENDO:
                    self.ts_ultimo_suelo = None
                    self.tiempo_en_suelo = 0.0
                    return "DE PIE"
                return "RECUPERANDOSE"
            self.ts_ultimo_suelo = None
            self.tiempo_en_suelo = 0.0

        return estado_base

    @property
    def alerta_critica(self):
        return self.tiempo_en_suelo >= SEGUNDOS_ALERTA_CRITICA

    @property
    def caida_confirmada(self):
        if len(self.estados) < FRAMES_CONFIRMAR:
            return False
        return all(
            e in ("CAYENDO", "EN EL SUELO")
            for e in self.estados
        )


# ── Tracker por IoU ──

class PersonTracker:
    def __init__(self):
        self._personas: dict[int, PersonState] = {}
        self._next_id = 0
        self._prev_boxes: dict[int, tuple] = {}
        self._sin_pose: dict[int, int] = {}

    def match(self, boxes_actuales):
        matched = {}
        used_prev = set()
        used_curr = set()

        pairs = []
        for ci, box_c in enumerate(boxes_actuales):
            for pid, box_p in self._prev_boxes.items():
                iou = _calcular_iou(box_c, box_p)
                if iou >= IOU_MIN_MATCH:
                    pairs.append((iou, ci, pid))

        pairs.sort(reverse=True)
        for _, ci, pid in pairs:
            if ci in used_curr or pid in used_prev:
                continue
            matched[ci] = pid
            used_curr.add(ci)
            used_prev.add(pid)

        for ci in range(len(boxes_actuales)):
            if ci not in matched:
                matched[ci] = self._next_id
                self._personas[self._next_id] = PersonState(boxes_actuales[ci])
                self._sin_pose[self._next_id] = 0
                self._next_id += 1

        new_prev = {}
        active_ids = set()
        for ci, pid in matched.items():
            new_prev[pid] = boxes_actuales[ci]
            active_ids.add(pid)

        for pid in list(self._personas):
            if pid not in active_ids:
                del self._personas[pid]
                self._sin_pose.pop(pid, None)

        self._prev_boxes = new_prev
        return matched

    def get_state(self, pid):
        return self._personas[pid]

    def marcar_sin_pose(self, pid):
        self._sin_pose[pid] = self._sin_pose.get(pid, 0) + 1

    def marcar_con_pose(self, pid):
        self._sin_pose[pid] = 0

    def es_objeto(self, pid):
        return self._sin_pose.get(pid, 0) >= MAX_FRAMES_SIN_POSE


# ── Main ──

def main():
    fuente = FUENTE_VIDEO
    if len(sys.argv) > 1:
        try:
            fuente = int(sys.argv[1])
        except ValueError:
            fuente = sys.argv[1]

    print(f"Abriendo fuente de video: {fuente}")
    print("  Tip: pasa el indice de camara como argumento:")
    print("    python webcam_fall.py 1    (segunda camara)")
    print("    python webcam_fall.py 2    (tercera camara)")
    print()

    cap = cv2.VideoCapture(fuente)

    if not cap.isOpened():
        print("=" * 50)
        print("ERROR: No se pudo abrir la camara/video.")
        print()
        print("Camaras disponibles:")
        for i in range(5):
            test = cv2.VideoCapture(i)
            if test.isOpened():
                w = int(test.get(cv2.CAP_PROP_FRAME_WIDTH))
                h = int(test.get(cv2.CAP_PROP_FRAME_HEIGHT))
                print(f"  Camara {i}: {w}x{h}")
                test.release()
            else:
                test.release()
        print()
        print("Ejecuta: python webcam_fall.py <numero>")
        print("=" * 50)
        return

    for _ in range(5):
        cap.read()

    ancho = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    alto = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps_real = cap.get(cv2.CAP_PROP_FPS) or 30
    print(f"Video abierto: {ancho}x{alto} @ {fps_real:.0f} FPS")
    print("Presiona 'q' para salir, 'f' para fullscreen.")
    print()

    window_name = "UKUCHA Fall Detector"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window_name, VENTANA_ANCHO, VENTANA_ALTO)

    tracker = PersonTracker()

    with mp_pose.Pose(
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5
    ) as pose:

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                if isinstance(fuente, str):
                    print("Video terminado.")
                else:
                    print("ERROR leyendo frame. Se desconecto la camara?")
                break

            now = time.monotonic()
            resultados = model(frame, verbose=False)

            current_boxes = []
            detections = []

            for resultado in resultados:
                if resultado.boxes is None or len(resultado.boxes) == 0:
                    continue
                for bbox, clase, conf in zip(
                    resultado.boxes.xyxy,
                    resultado.boxes.cls,
                    resultado.boxes.conf,
                ):
                    if int(clase) != 0:
                        continue
                    if float(conf) < MIN_CONFIANZA_YOLO:
                        continue
                    x1, y1, x2, y2 = map(int, bbox)
                    if (y2 - y1) < MIN_ALTO_BBOX or (x2 - x1) < 20:
                        continue
                    current_boxes.append((x1, y1, x2, y2))
                    detections.append(float(conf))

            matched = tracker.match(current_boxes)
            hay_alerta = False
            hay_critica = False

            for ci, pid in matched.items():
                x1, y1, x2, y2 = current_boxes[ci]
                conf = detections[ci]
                ancho_box = x2 - x1
                alto_box = y2 - y1

                # Filtro de proporcion humana minima
                aspect_bbox = alto_box / max(ancho_box, 1)
                if aspect_bbox < MIN_ASPECT_HUMANO:
                    tracker.marcar_sin_pose(pid)
                    continue

                # Si ya fue marcado como objeto, solo mostrar borde gris
                if tracker.es_objeto(pid):
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (80, 80, 80), 1)
                    continue

                y1c = max(0, y1)
                y2c = min(frame.shape[0], y2)
                x1c = max(0, x1)
                x2c = min(frame.shape[1], x2)
                persona = frame[y1c:y2c, x1c:x2c]

                if persona.size == 0:
                    continue

                persona_rgb = cv2.cvtColor(persona, cv2.COLOR_BGR2RGB)

                try:
                    pose_result = pose.process(persona_rgb)
                except Exception:
                    continue

                if not pose_result.pose_landmarks:
                    tracker.marcar_sin_pose(pid)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (128, 128, 128), 1)
                    continue

                tracker.marcar_con_pose(pid)

                lm = pose_result.pose_landmarks.landmark
                modo = evaluar_visibilidad(lm, alto_box, ancho_box,
                                           frame.shape[0], frame.shape[1])

                if modo == 'muy_cerca':
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (100, 100, 255), 2)
                    cv2.putText(frame, "MUY CERCA - alejarse",
                                (x1 + 5, y1 + 25),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (100, 100, 255), 2)
                    continue

                if modo == 'insuficiente':
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (128, 128, 128), 1)
                    continue

                if not pose_result.pose_world_landmarks:
                    continue

                wl = pose_result.pose_world_landmarks.landmark
                h_p, w_p = persona.shape[:2]

                try:
                    score, dbg = calcular_score_caida(
                        lm, wl, w_p, h_p, alto_box, ancho_box,
                        modo_visibilidad=modo
                    )
                except (IndexError, AttributeError):
                    continue

                ps = tracker.get_state(pid)
                sentado_geo = dbg.get('sentado', False)
                estado = ps.update(current_boxes[ci], score, now,
                                   sentado_geometrico=sentado_geo)
                score_display = ps.score_smooth

                if modo == 'parcial':
                    color = COLORES["PARCIAL"]
                    estado_display = f"~{estado}"
                else:
                    color = COLORES.get(estado, (200, 200, 200))
                    estado_display = estado

                if ps.caida_confirmada and modo == 'completo':
                    hay_alerta = True
                if ps.alerta_critica and modo == 'completo':
                    hay_critica = True

                if MOSTRAR_LANDMARKS:
                    mp_drawing.draw_landmarks(
                        persona, pose_result.pose_landmarks,
                        mp_pose.POSE_CONNECTIONS
                    )
                    frame[y1c:y2c, x1c:x2c] = persona

                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

                t3 = f"{dbg['torso3d']:.0f}" if dbg['torso3d'] is not None else "-"
                cm = f"{dbg['compact']:.1f}" if dbg['compact'] is not None else "-"
                ns = dbg.get('n_signals', 0)
                label = f"{estado_display} T:{t3} C:{cm} S:{score_display:.0%} [{ns}s]"
                (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
                cv2.rectangle(frame, (x1, y1 - th - 10), (x1 + tw, y1), color, -1)
                cv2.putText(frame, label, (x1, y1 - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

                if ps.alerta_critica and modo == 'completo':
                    secs = f"{ps.tiempo_en_suelo:.0f}s"
                    cv2.putText(frame, secs, (x1, y2 + 20),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

            if hay_critica:
                blink = int(now * 4) % 2 == 0
                if blink:
                    cv2.putText(frame, "!! EMERGENCIA !!",
                                (30, 60), cv2.FONT_HERSHEY_SIMPLEX,
                                1.0, (0, 0, 255), 3)
                    cv2.putText(frame, "PERSONA EN EL SUELO",
                                (30, 100), cv2.FONT_HERSHEY_SIMPLEX,
                                0.8, (0, 0, 255), 2)
            elif hay_alerta:
                cv2.putText(frame, "!! CAIDA DETECTADA !!",
                            (30, 70), cv2.FONT_HERSHEY_SIMPLEX,
                            0.9, (0, 0, 255), 3)

            cv2.putText(frame, "UKUCHA Fall Detector | 'q' salir | 'f' fullscreen",
                        (10, frame.shape[0] - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

            cv2.imshow(window_name, frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                break
            elif key == ord('f'):
                prop = cv2.getWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN)
                if prop == cv2.WINDOW_FULLSCREEN:
                    cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN,
                                          cv2.WINDOW_NORMAL)
                else:
                    cv2.setWindowProperty(window_name, cv2.WND_PROP_FULLSCREEN,
                                          cv2.WINDOW_FULLSCREEN)

    cap.release()
    cv2.destroyAllWindows()
    print("Finalizado.")


if __name__ == "__main__":
    main()
