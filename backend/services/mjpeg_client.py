"""MjpegClient: lee el stream HTTP MJPEG multipart que expone el ESP32-CAM
(ver appflores/esp32cam_firmware.ino: `multipart/x-mixed-replace`, un JPEG
completo por parte, sin fragmentar) y entrega cada frame decodificado via
callback en el mismo formato que antes consumia FrameReassembler.submit_frame
(frame_id, jpeg_bytes, timestamp_ms) -- para no tener que tocar
DetectionWorker/DetectionService.

Reemplaza el reensamblado de chunks fragmentados (services/frame_reassembler.py,
ya no se usa en app.py): el hardware real no fragmenta video sobre el
enlace de sensores. El ESP32-CAM sirve su propio servidor HTTP en un canal
WiFi separado del ESP32-S3 de telemetria; ese servidor ya entrega un frame
JPEG completo por respuesta, no hace falta reensamblar nada del lado PC.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Callable, Optional

import requests

logger = logging.getLogger(__name__)

FrameCallback = Callable[[int, bytes, int], None]

_CONNECT_TIMEOUT_S = 5.0
# El read timeout es mas generoso que el connect timeout: el stream MJPEG
# tiene huecos naturales entre frame y frame (captura + conversion JPEG
# por software en el ESP32-CAM, mas jitter de WiFi 2.4GHz) que pueden
# superar unos pocos segundos sin que el enlace este realmente caido.
_READ_TIMEOUT_S = 20.0
_CHUNK_SIZE = 4096
_MAX_BUFFER_WITHOUT_SOI = 1_000_000  # evita crecer sin limite si nunca aparece un SOI
_RECONNECT_BACKOFF_INITIAL_S = 1.0
_RECONNECT_BACKOFF_MAX_S = 15.0

_JPEG_SOI = b"\xff\xd8"  # Start Of Image
_JPEG_EOI = b"\xff\xd9"  # End Of Image


class MjpegClient:
    def __init__(self, url: str, on_frame: FrameCallback):
        self._url = url
        self._on_frame = on_frame
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._frame_id = 0

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True, name="MjpegClient")
        self._thread.start()
        logger.info("MjpegClient iniciado (url=%s)", self._url)

    def stop(self) -> None:
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=3.0)
            self._thread = None
        logger.info("MjpegClient detenido")

    def _run(self) -> None:
        backoff = _RECONNECT_BACKOFF_INITIAL_S
        while self._running:
            try:
                self._stream_once()
                backoff = _RECONNECT_BACKOFF_INITIAL_S
            except Exception as e:
                if not self._running:
                    break
                logger.error(
                    "Enlace con ESP32-CAM caido (%s); reintento en %.1fs", e, backoff
                )
                time.sleep(backoff)
                backoff = min(backoff * 2, _RECONNECT_BACKOFF_MAX_S)

    def _stream_once(self) -> None:
        with requests.get(
            self._url, stream=True, timeout=(_CONNECT_TIMEOUT_S, _READ_TIMEOUT_S)
        ) as resp:
            resp.raise_for_status()
            buffer = b""
            for chunk in resp.iter_content(chunk_size=_CHUNK_SIZE):
                if not self._running:
                    return
                buffer = self._extract_frames(buffer + chunk)

    def _extract_frames(self, buffer: bytes) -> bytes:
        """Extrae frames JPEG completos (delimitados por marcadores SOI/EOI)
        del buffer multipart acumulado; devuelve el resto sin consumir para
        la siguiente iteracion."""
        while True:
            start = buffer.find(_JPEG_SOI)
            if start == -1:
                if len(buffer) > _MAX_BUFFER_WITHOUT_SOI:
                    logger.warning("Buffer MJPEG sin marcador SOI, se descarta")
                    return b""
                return buffer
            end = buffer.find(_JPEG_EOI, start + 2)
            if end == -1:
                return buffer[start:]
            jpeg_bytes = buffer[start:end + 2]
            buffer = buffer[end + 2:]
            self._frame_id += 1
            try:
                self._on_frame(self._frame_id, jpeg_bytes, int(time.time() * 1000))
            except Exception:
                logger.exception("on_frame fallo para frame_id=%d", self._frame_id)


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    url = sys.argv[1] if len(sys.argv) > 1 else "http://192.168.4.1/"

    def _on_frame(frame_id: int, jpeg_bytes: bytes, timestamp_ms: int) -> None:
        logger.info("Frame %d: %d bytes @ %d", frame_id, len(jpeg_bytes), timestamp_ms)

    client = MjpegClient(url, on_frame=_on_frame)
    client.start()
    try:
        time.sleep(15.0)
    except KeyboardInterrupt:
        pass
    finally:
        client.stop()
