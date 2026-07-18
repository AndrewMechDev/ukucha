"""
rescue_detector.py — Deteccion de entorno de rescate (escombros/accesos),
modulo reusable.

Modelo: drespnet_best.pt, YOLOv8s-seg fine-tuneado en DRespNeT filtrado
a 11 clases (civilian_visible, group_of_civilians, rescue_team, rubble,
debris_heavy/light/moderate, entry_door/window_accessible/blocked).
Entrenado por el equipo (Anderbstz/data) con dataset CC BY 4.0.

CAVEAT CONOCIDO: DRespNeT fue entrenado con imagenes AEREAS (dron/UAV).
Con camara horizontal/terrestre habra domain shift: la deteccion de
rubble/debris/accesos sera menos confiable que en el paper original.
Metricas del modelo en test: Box mAP@50 ~= 0.30, Mask mAP@50 ~= 0.31.

Costoso en GPU (segmentacion). En el pipeline unificado se corre cada
N frames (ver --env-every en run_ukucha_dual.py del equipo) para
mantener FPS.

Modulo standalone: correr `python detectors/rescue_detector.py` para
probar solo esta capa con la webcam.
"""
from pathlib import Path

from ultralytics import YOLO

MODELO_DRESPNET = str(Path(__file__).resolve().parents[1] / "models" / "drespnet_best.pt")

ACCESS_CLASSES = {"entry_door_accessible", "entry_window_accessible"}
HAZARD_CLASSES = {"rubble", "debris_heavy", "debris_light", "debris_moderate"}
CIVILIAN_CLASSES = {"civilian_visible", "group_of_civilians"}
RESCUE_CLASSES = {"rescue_team"}
BLOCKED_CLASSES = {"entry_door_blocked", "entry_window_blocked"}

CONF_ENV_DEFAULT = 0.35


class RescueDetector:
    """
    Encapsula YOLO (drespnet_best.pt, seg). Uso:
        rd = RescueDetector()
        result = rd.process(frame)          # result.plot() para frame anotado
        accesses = rd.extract_access(result)
    No dibuja in-place: usar result.plot() (devuelve un frame anotado nuevo),
    igual que hace run_ukucha_dual.py, porque el modelo es de segmentacion
    (mascaras, no solo cajas).
    """

    def __init__(self, model_path=MODELO_DRESPNET, device=None):
        self.model = YOLO(model_path)
        if device is not None:
            self.model.to(device)
        self.device = device

    def process(self, infer_frame, conf_env=CONF_ENV_DEFAULT):
        """
        infer_frame: frame LIMPIO usado unicamente para inferencia. No debe
            llegar con anotaciones de otros detectores dibujadas encima.
        No dibuja nada — el llamador compone el resultado sobre su propio
        canvas con `result.plot(img=canvas)`.
        """
        results = self.model.predict(infer_frame, conf=conf_env, device=self.device, verbose=False)
        return results[0] if results else None

    def extract_access(self, result, conf_env=CONF_ENV_DEFAULT):
        """Devuelve lista de (name, box) de accesos transitables."""
        out = []
        if result is None or result.boxes is None:
            return out
        names = self.model.names
        for b in result.boxes:
            if float(b.conf[0]) < conf_env:
                continue
            name = names.get(int(b.cls[0]), str(int(b.cls[0])))
            if name in ACCESS_CLASSES:
                out.append((name, [float(v) for v in b.xyxy[0]]))
        return out

    def extract_hazards(self, result, conf_env=CONF_ENV_DEFAULT):
        """Extract rubble/debris, civilians, rescue teams, and blocked access."""
        empty = {"hazards": [], "civilians": [], "rescue_teams": [], "blocked": []}
        if result is None or result.boxes is None:
            return empty
        names = self.model.names
        hazards, civilians, rescue_teams, blocked = [], [], [], []
        for b in result.boxes:
            conf = float(b.conf[0])
            if conf < conf_env:
                continue
            name = names.get(int(b.cls[0]), str(int(b.cls[0])))
            box = [float(v) for v in b.xyxy[0]]
            entry = (name, box, conf)
            if name in HAZARD_CLASSES:
                hazards.append(entry)
            elif name in CIVILIAN_CLASSES:
                civilians.append(entry)
            elif name in RESCUE_CLASSES:
                rescue_teams.append(entry)
            elif name in BLOCKED_CLASSES:
                blocked.append(entry)
        return {"hazards": hazards, "civilians": civilians,
                "rescue_teams": rescue_teams, "blocked": blocked}

    def count_detections(self, result):
        return 0 if (result is None or result.boxes is None) else len(result.boxes)


def _standalone_main():
    """Prueba independiente: solo capa de entorno/escombros con webcam."""
    import time
    import cv2

    print("Cargando RescueDetector (DRespNeT best.pt)...")
    detector = RescueDetector()
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("ERROR: no se pudo abrir la camara.")
        return

    print("ADVERTENCIA: modelo entrenado con imagenes aereas (dron).")
    print("Con camara terrestre la deteccion sera menos confiable (domain shift).")
    print("Presiona 'q' para salir.")
    prev_time = time.time()
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            result = detector.process(frame)
            annotated = result.plot() if result is not None else frame
            now = time.time()
            fps = 1.0 / max(now - prev_time, 1e-6)
            prev_time = now
            n = detector.count_detections(result)
            cv2.putText(annotated, f"FPS: {fps:.1f}  Detecciones entorno: {n}",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            cv2.imshow("Rescue Detector / DRespNeT (standalone)", annotated)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    _standalone_main()
