"""Puerto de persistencia: contrato para guardar eventos de deteccion,
telemetria historica, y log de comandos. Cualquier backend (Supabase, otro
Postgres, un archivo local a futuro) implementa este Protocol -- la capa de
negocio (PersistenceWorker) nunca depende de Supabase directamente.
"""
from __future__ import annotations

from typing import Protocol


class PersistenceBackend(Protocol):
    def save_event(self, event: dict) -> None:
        """Evento de deteccion relevante (caida, victima bajo escombros, etc)."""
        ...

    def save_telemetry(self, record: dict) -> None:
        """Registro historico de audio_sensors o env_and_actuation."""
        ...

    def save_command_log(self, record: dict) -> None:
        """Entrada de auditoria: comando enviado, confirmado, o sin ack."""
        ...
