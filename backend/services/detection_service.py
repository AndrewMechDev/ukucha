"""DetectionService: corre el pipeline completo de deteccion (caidas + EPP +
entorno/escombros + fusion) sobre frames JPEG ya reensamblados por
FrameReassembler.

Reusa exactamente detectors/fall_detector.py, detectors/epp_detector.py,
detectors/rescue_detector.py y la logica de fusion de ukucha_detector.py
(classify_rubble_victims, link_victims_access, draw_blocked_access,
pick_device) — nada se reimplementa aca, solo se orquesta sobre una fuente
de frames distinta a la webcam (JPEG reensamblado desde el enlace serial
en vez de WebcamStream).
"""
from __future__ import annotations

import logging
import time
from math import hypot
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

from detectors.epp_detector import CONF_EPP_DEFAULT, CONF_VICTIM_DEFAULT, EppDetector
from detectors.fall_detector import FallDetector
from detectors.rescue_detector import CONF_ENV_DEFAULT, RescueDetector
from ukucha_detector import (
    classify_rubble_victims,
    draw_blocked_access,
    link_victims_access,
    pick_device,
)

logger = logging.getLogger(__name__)

_JPEG_QUALITY = 85


class DetectionService:
    """Instancia los 3 detectores una sola vez y expone process_jpeg() para
    correr el pipeline completo sobre un frame JPEG reensamblado.

    No depende de FastAPI ni del enlace serial: recibe bytes JPEG crudos y
    devuelve un dict con los resultados de cada capa + el canvas anotado
    re-codificado. La adaptacion a un esquema de salida validado (Pydantic)
    para el WebSocket es responsabilidad de la capa API (Fase 4).
    """

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
        self.device = device if device is not None else pick_device()
        logger.info(
            "DetectionService: dispositivo=%s", "cuda:0" if self.device == 0 else self.device
        )

        self._check_models(enable_fall, enable_epp, enable_rescue)

        self.env_every = max(1, env_every)
        self.conf_victim = conf_victim
        self.conf_epp = conf_epp
        self.conf_env = conf_env
        self.route_frac = route_frac
        self.show_all_epp = show_all_epp

        self.fall_detector = FallDetector(device=self.device) if enable_fall else None
        self.epp_detector = EppDetector(device=self.device) if enable_epp else None
        self.rescue_detector = RescueDetector(device=self.device) if enable_rescue else None

        self._frame_idx = 0
        self._last_env_result = None
        logger.info("DetectionService listo (fall=%s epp=%s rescue=%s, env_every=%d)",
                    enable_fall, enable_epp, enable_rescue, self.env_every)

    @staticmethod
    def _check_models(enable_fall: bool, enable_epp: bool, enable_rescue: bool) -> None:
        models_dir = Path(__file__).resolve().parents[2] / "models"
        required = []
        if enable_fall:
            required.append(("yolov8n.pt", "fall detector"))
        if enable_epp:
            required.append(("epp_yolo8m.pt", "EPP detector"))
        if enable_rescue:
            required.append(("drespnet_best.pt", "rescue detector"))
        for fname, desc in required:
            path = models_dir / fname
            if not path.exists():
                raise FileNotFoundError(
                    f"No se encontro models/{fname} (requerido por {desc}). "
                    f"Colocar el archivo en: {path}"
                )

    def close(self) -> None:
        if self.fall_detector is not None:
            self.fall_detector.close()

    def process_jpeg(self, frame_id: int, jpeg_bytes: bytes, timestamp_ms: int) -> Optional[dict]:
        """Decodifica, corre el pipeline completo, y devuelve un dict con
        los resultados crudos de cada capa + el canvas anotado re-codificado
        a JPEG. None si el JPEG no se pudo decodificar."""
        frame = cv2.imdecode(np.frombuffer(jpeg_bytes, np.uint8), cv2.IMREAD_COLOR)
        if frame is None:
            logger.warning("Frame %d: JPEG reensamblado no se pudo decodificar", frame_id)
            return None

        self._frame_idx += 1
        now = time.monotonic()
        h, w = frame.shape[:2]
        diag = hypot(w, h)

        # Copia limpia para inferencia; 'frame' es el canvas que acumula las
        # anotaciones de las 3 capas (mismo patron que ukucha_detector.py).
        infer_frame = frame.copy()

        fall_result = {"hay_alerta": False, "hay_critica": False, "personas": []}
        if self.fall_detector is not None:
            fall_result = self.fall_detector.process(
                infer_frame, now, mostrar_landmarks=True, device=self.device, canvas=frame
            )

        accesses, hazards, civilians, rescue_teams, blocked = [], [], [], [], []
        n_env = 0
        if self.rescue_detector is not None:
            recompute_env = (
                self.env_every <= 1
                or self._frame_idx % self.env_every == 0
                or self._last_env_result is None
            )
            if recompute_env:
                self._last_env_result = self.rescue_detector.process(
                    infer_frame, conf_env=self.conf_env
                )
                if self._last_env_result is not None:
                    frame[:] = self._last_env_result.plot(img=frame)
            if self._last_env_result is not None:
                accesses = self.rescue_detector.extract_access(
                    self._last_env_result, conf_env=self.conf_env
                )
                env_info = self.rescue_detector.extract_hazards(
                    self._last_env_result, conf_env=self.conf_env
                )
                hazards = env_info["hazards"]
                civilians = env_info["civilians"]
                rescue_teams = env_info["rescue_teams"]
                blocked = env_info["blocked"]
                n_env = self.rescue_detector.count_detections(self._last_env_result)

        victims, n_rescuer, n_epp, bodyparts = [], 0, 0, []
        if self.epp_detector is not None:
            info_epp = self.epp_detector.process(
                infer_frame, conf_victim=self.conf_victim, conf_epp=self.conf_epp,
                show_all_epp=self.show_all_epp, canvas=frame,
            )
            victims = info_epp["victims"]
            n_rescuer = info_epp["n_rescuer"]
            n_epp = info_epp["n_epp"]
            bodyparts = info_epp.get("bodyparts", [])

        n_routes = 0
        if victims and accesses:
            n_routes = link_victims_access(frame, victims, accesses, self.route_frac * diag)

        fusion = {"rubble_victims": [], "n_fall_rubble": 0, "n_risk_zones": 0, "n_civilians": 0}
        if hazards or civilians:
            fusion = classify_rubble_victims(
                frame, bodyparts, hazards, civilians, victims, fall_result.get("personas", [])
            )

        if blocked:
            draw_blocked_access(frame, blocked)

        ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, _JPEG_QUALITY])
        if not ok:
            logger.warning(
                "Frame %d: no se pudo re-codificar el canvas anotado, se reenvia el original",
                frame_id,
            )
        annotated_jpeg = buf.tobytes() if ok else jpeg_bytes

        return {
            "frame_id": frame_id,
            "timestamp_ms": timestamp_ms,
            "annotated_jpeg": annotated_jpeg,
            "fall": fall_result,
            "epp": {
                "victims": victims, "n_rescuer": n_rescuer, "n_epp": n_epp, "bodyparts": bodyparts,
            },
            "env": {
                "accesses": accesses, "hazards": hazards, "civilians": civilians,
                "rescue_teams": rescue_teams, "blocked": blocked, "n_env": n_env,
            },
            "fusion": {**fusion, "n_routes": n_routes},
        }


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    from backend.adapters.mock_transport import MockTransport
    from backend.schemas.uplink import FramePacket, UplinkPacket
    from backend.services.frame_reassembler import FrameReassembler
    from backend.services.serial_manager import SerialManager

    logger.info("Cargando DetectionService (puede tardar por la carga de los 3 modelos)...")
    t0 = time.monotonic()
    service = DetectionService(env_every=5)
    logger.info("DetectionService cargado en %.1fs", time.monotonic() - t0)

    stats = {"frames": 0, "recompute_env": 0, "total_latency_s": 0.0}

    def _on_frame_complete(frame_id: int, jpeg_bytes: bytes, timestamp_ms: int) -> None:
        t_start = time.monotonic()
        result = service.process_jpeg(frame_id, jpeg_bytes, timestamp_ms)
        latency = time.monotonic() - t_start
        if result is None:
            logger.error("Frame %d: process_jpeg devolvio None", frame_id)
            return
        stats["frames"] += 1
        stats["total_latency_s"] += latency
        img = cv2.imdecode(np.frombuffer(result["annotated_jpeg"], np.uint8), cv2.IMREAD_COLOR)
        ok_decode = img is not None
        logger.info(
            "Frame %d: %.0fms | victimas=%d rescatistas=%d epp=%d | "
            "alerta_caida=%s critica=%s | env=%d rubble_victims=%d | jpeg_anotado_valido=%s",
            frame_id, latency * 1000,
            len(result["epp"]["victims"]), result["epp"]["n_rescuer"], result["epp"]["n_epp"],
            result["fall"]["hay_alerta"], result["fall"]["hay_critica"],
            result["env"]["n_env"], len(result["fusion"]["rubble_victims"]),
            ok_decode,
        )

    reassembler = FrameReassembler(on_frame_complete=_on_frame_complete, timeout_s=2.0)
    reassembler.start()

    def _on_packet(packet: UplinkPacket) -> None:
        if isinstance(packet, FramePacket):
            reassembler.add_chunk(packet)

    manager = SerialManager(transport=MockTransport(seed=3), on_packet=_on_packet)
    manager.start()

    try:
        time.sleep(6.0)
    except KeyboardInterrupt:
        pass
    finally:
        manager.stop()
        reassembler.stop()
        service.close()
        avg_ms = (stats["total_latency_s"] / stats["frames"] * 1000) if stats["frames"] else 0.0
        logger.info(
            "Resumen: %d frames procesados, latencia promedio %.0fms/frame",
            stats["frames"], avg_ms,
        )
