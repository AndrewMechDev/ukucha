"""Paquetes de bajada (PC -> nodo) enviados por el enlace serial hacia No3."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class DownlinkCommand(BaseModel):
    target_node: Literal["esp32_s3_no1", "esp32_s3_no2"]
    cmd_id: int
    command: str
    params: dict = Field(default_factory=dict)
