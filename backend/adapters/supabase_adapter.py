"""Adapter de PersistenceBackend sobre Supabase (Postgres).

Requiere SUPABASE_URL y SUPABASE_KEY (service role o anon con policies
apropiadas). Import de `supabase` es perezoso (dentro de __init__), asi
el resto del backend no depende de que el paquete este instalado si no
se va a usar Supabase (ver backend/adapters/null_adapter.py).

Las 3 tablas esperadas (ver backend/supabase_schema.sql para crearlas):
    detection_events, telemetry_history, command_log

Cada metodo hace un insert simple. Los errores se propagan al llamador
(PersistenceWorker) que los captura y los silencia con backoff de logging
-- este adapter NO debe manejar reintentos ni backpressure, esa
responsabilidad es de PersistenceWorker.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

TABLE_EVENTS = "detection_events"
TABLE_TELEMETRY = "telemetry_history"
TABLE_COMMANDS = "command_log"


class SupabaseAdapter:
    def __init__(self, url: str, key: str):
        from supabase import Client, create_client  # import perezoso

        self._client: "Client" = create_client(url, key)
        logger.info("SupabaseAdapter conectado a %s", url)

    def save_event(self, event: dict) -> None:
        self._insert(TABLE_EVENTS, event)

    def save_telemetry(self, record: dict) -> None:
        self._insert(TABLE_TELEMETRY, record)

    def save_command_log(self, record: dict) -> None:
        self._insert(TABLE_COMMANDS, record)

    def _insert(self, table: str, record: dict) -> None:
        self._client.table(table).insert(record).execute()
