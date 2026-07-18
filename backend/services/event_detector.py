"""EventDetector: decide que salidas del pipeline son 'eventos relevantes'
para persistir, usando la misma logica de borde de subida (transicion
False->True) que ServerNotifier ya usa en ukucha_detector.py -- evita
escribir el mismo evento en cada frame mientras la alerta se mantiene
activa, y evita perder la coordenada GPS del momento en que ocurrio.
"""
from __future__ import annotations

from typing import List

from backend.schemas.output import EnrichedFrameOutput


class EventDetector:
    def __init__(self):
        self._prev_alerta = False
        self._prev_critica = False
        self._prev_rubble = False

    def detect(self, output: EnrichedFrameOutput) -> List[dict]:
        events: List[dict] = []
        gps = output.env.gps.model_dump() if output.env.gps is not None else None

        if output.fall.hay_critica and not self._prev_critica:
            events.append({
                "tipo": "caida_critica", "frame_id": output.frame_id,
                "event_timestamp": output.timestamp, "gps": gps,
                "detalle": "persona en el suelo por tiempo prolongado",
            })
        elif output.fall.hay_alerta and not self._prev_alerta:
            events.append({
                "tipo": "caida_detectada", "frame_id": output.frame_id,
                "event_timestamp": output.timestamp, "gps": gps,
            })
        self._prev_alerta = output.fall.hay_alerta
        self._prev_critica = output.fall.hay_critica

        rubble_now = output.fusion.n_rubble_victims > 0
        if rubble_now and not self._prev_rubble:
            events.append({
                "tipo": "persona_bajo_escombros", "frame_id": output.frame_id,
                "event_timestamp": output.timestamp, "gps": gps,
                "detalle": f"{output.fusion.n_rubble_victims} victima(s)",
            })
        self._prev_rubble = rubble_now

        return events
