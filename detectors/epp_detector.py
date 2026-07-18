"""
epp_detector.py — Deteccion de EPP (Equipo de Proteccion Personal) y
clasificacion victima/rescatista, modulo reusable.

Modelo: yolo8m.pt (SH17, 17 clases: person, helmet, safety-vest, gloves,
ear-mufs, etc). Entrenado por el equipo (Anderbstz/data), reusado aqui.

Logica adaptada de run_ukucha_dual.py (analyze_people): una persona con
EPP fuerte encima (casco/chaleco/traje) se clasifica como RESCATISTA
(verde); sin EPP, como VICTIMA (rojo). Partes de cuerpo aisladas
(mano/pie/cabeza) fuera de cualquier persona tambien cuentan como
posible victima.

Modelo standalone: correr `python detectors/epp_detector.py` para probar
solo esta capa con la webcam.
"""
from pathlib import Path

import cv2
from ultralytics import YOLO

MODELO_EPP = str(Path(__file__).resolve().parents[1] / "models" / "epp_yolo8m.pt")

PERSON_CLASS = "person"
BODYPART = {"head", "face", "hands", "foot"}
RESCUER_SIGNAL = {"helmet", "safety-vest", "safety-suit", "medical-suit"}
EQUIP_OTHER = {"gloves", "face-mask", "face-guard", "glasses", "shoes", "ear-mufs", "tool"}

COL_VICTIM = (0, 0, 255)      # rojo
COL_RESCUER = (0, 200, 0)     # verde
COL_EQUIP = (0, 165, 255)     # naranja

CONF_VICTIM_DEFAULT = 0.25    # umbral bajo: recall de victimas/personas
CONF_EPP_DEFAULT = 0.30       # umbral para EPP de rescatista (casco/chaleco)

BODYPART_ES = {"head": "cabeza", "face": "rostro", "hands": "manos", "foot": "pie"}


def _center(xyxy):
    x1, y1, x2, y2 = xyxy
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


def _inside(pt, box):
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
    x1, y1, x2, y2 = map(int, box)
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
    cv2.rectangle(frame, (x1, y1 - th - 6), (x1 + tw + 4, y1), color, -1)
    cv2.putText(frame, text, (x1 + 2, y1 - 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)


class EppDetector:
    """
    Encapsula YOLO (yolo8m.pt, SH17) con tracking ByteTrack. Uso:
        ed = EppDetector()
        info = ed.process(frame)
        # info = {"victims": [(tid, bbox, confirmable), ...], "n_rescuer": int, "n_epp": int}
        # confirmable=True: persona completa detectada (puede confirmarse como evidencia)
        # confirmable=False: parte de cuerpo aislada (solo visual, no dispara evidencia)
    Dibuja directamente sobre el frame recibido (in-place).
    """

    def __init__(self, model_path=MODELO_EPP, device=None):
        self.model = YOLO(model_path)
        if device is not None:
            self.model.to(device)
        self.device = device

    def process(self, infer_frame, conf_victim=CONF_VICTIM_DEFAULT,
                conf_epp=CONF_EPP_DEFAULT, show_all_epp=False, track=True,
                canvas=None):
        """
        infer_frame: frame LIMPIO usado unicamente para inferencia. No debe
            llegar con anotaciones de otros detectores dibujadas encima.
        canvas: frame donde se dibujan las cajas. Si es None, se usa
            infer_frame (uso standalone).
        """
        if canvas is None:
            canvas = infer_frame

        if track:
            results = self.model.track(
                infer_frame, persist=True, conf=min(conf_victim, conf_epp),
                device=self.device, verbose=False, tracker="bytetrack.yaml",
            )
        else:
            results = self.model.predict(
                infer_frame, conf=min(conf_victim, conf_epp),
                device=self.device, verbose=False,
            )

        if not results:
            return {"victims": [], "n_rescuer": 0, "n_epp": 0}

        result = results[0]
        names = self.model.names

        persons, parts, equip = [], [], []
        if result.boxes is not None:
            for b in result.boxes:
                conf = float(b.conf[0])
                name = names.get(int(b.cls[0]), str(int(b.cls[0])))
                xyxy = [float(v) for v in b.xyxy[0]]
                tid = _box_id(b)
                if name == PERSON_CLASS and conf >= conf_victim:
                    persons.append((tid, xyxy))
                elif name in BODYPART and conf >= conf_victim:
                    parts.append((tid, name, xyxy))
                elif (name in RESCUER_SIGNAL or (show_all_epp and name in EQUIP_OTHER)) and conf >= conf_epp:
                    equip.append((name, xyxy, conf, name in RESCUER_SIGNAL))

        rescuer_boxes = [xy for (nm, xy, _, strong) in equip if strong]

        victims = []
        n_rescuer = 0
        for tid, pbox in persons:
            if any(_inside(_center(rb), pbox) for rb in rescuer_boxes):
                _label_box(canvas, pbox, COL_RESCUER,
                           f"RESCATISTA{'' if tid is None else ' #' + str(tid)}")
                n_rescuer += 1
            else:
                _label_box(canvas, pbox, COL_VICTIM,
                           f"VICTIMA{'' if tid is None else ' #' + str(tid)}")
                victims.append((tid, pbox, True))

        isolated_parts = []
        for tid, nm, xy in parts:
            c = _center(xy)
            if any(_inside(c, pb) for _, pb in persons):
                continue
            nm_es = BODYPART_ES.get(nm, nm)
            _label_box(canvas, xy, COL_VICTIM,
                       f"VICTIMA? {nm_es}{'' if tid is None else ' #' + str(tid)}")
            victims.append((tid, xy, False))
            isolated_parts.append((tid, nm, xy))

        for nm, xy, conf, _ in equip:
            _label_box(canvas, xy, COL_EQUIP, f"EPP:{nm} {conf:.2f}")

        return {"victims": victims, "n_rescuer": n_rescuer, "n_epp": len(equip),
                "bodyparts": isolated_parts}


def _standalone_main():
    """Prueba independiente: solo capa EPP con webcam."""
    import time

    print("Cargando EppDetector (yolo8m.pt)...")
    detector = EppDetector()
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("ERROR: no se pudo abrir la camara.")
        return

    print("Presiona 'q' para salir.")
    prev_time = time.time()
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            info = detector.process(frame)
            now = time.time()
            fps = 1.0 / max(now - prev_time, 1e-6)
            prev_time = now
            cv2.putText(frame, f"FPS: {fps:.1f}  Victimas: {len(info['victims'])}  "
                                f"Rescatistas: {info['n_rescuer']}  EPP: {info['n_epp']}",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            cv2.imshow("EPP Detector (standalone)", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    _standalone_main()
