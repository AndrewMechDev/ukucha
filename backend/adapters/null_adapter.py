"""NullPersistenceAdapter: implementa PersistenceBackend sin escribir a
ningun lado -- solo loguea. Es el adapter por defecto cuando SUPABASE_URL/
SUPABASE_KEY no estan configurados, para poder desarrollar y probar todo
el backend (incluyendo los hooks de persistencia) sin depender de tener un
proyecto Supabase real armado.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class NullPersistenceAdapter:
    def save_event(self, event: dict) -> None:
        logger.info("[persistencia-null] evento: %s", event)

    def save_telemetry(self, record: dict) -> None:
        logger.info("[persistencia-null] telemetria: kind=%s node_id=%s",
                     record.get("kind"), record.get("node_id"))

    def save_command_log(self, record: dict) -> None:
        logger.info("[persistencia-null] comando: cmd_id=%s event=%s",
                     record.get("cmd_id"), record.get("event"))
