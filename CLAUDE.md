# UKUCHA Fall Detector

Este es el monorepo `ukucha` (ver `README.md` para la vista general de
`backend/` + `frontend/`). Este documento cubre especificamente la capa de
vision/deteccion y el backend v2 de hardware, migrados desde el repo de
desarrollo `test-yolo` (rama `feature/conexion`) siguiendo las skills en
`.claude/skills/ukucha/`.

Sistema de seguridad minera/SAR: deteccion de caidas, EPPs faltantes, y
personas bajo escombros. Dos pipelines de captura comparten la misma capa
de deteccion (ver `.claude/skills/ukucha/sistema.md`):

1. **Webcam** (`ukucha_detector.py` / `webcam_fall.py`) — demo local.
2. **Hardware ESP32** (`backend/`) — pipeline serial+deteccion+WS+Supabase
   para el robot real (4 placas: ESP32-CAM + 3x ESP32-S3). Ver
   `.claude/skills/ukucha/backend-conexion.md`.

## Stack

- Python 3.12 con venv local (`venv/`)
- YOLOv8 (ultralytics): personas, EPP (SH17), escombros/DRespNeT (3 modelos)
- MediaPipe Pose para estimacion de postura (2D + 3D world landmarks)
- OpenCV para captura y visualizacion
- FastAPI: `server.py` (telemetria de gases, legado) y `backend/app.py`
  (pipeline completo sobre hardware ESP32, WebSocket + Supabase)
- pyserial (enlace full-duplex con el hardware), supabase-py (persistencia)

## Ejecutar

```bash
# Demo webcam (los 3 detectores + fusion)
venv\Scripts\python.exe ukucha_detector.py

# Backend sobre hardware ESP32 (o simulado con MockTransport por defecto)
venv\Scripts\python.exe -m uvicorn backend.app:app --host 0.0.0.0 --port 8000
```

## Estructura

- `ukucha_detector.py` — pipeline unificado webcam (3 detectores + fusion)
- `webcam_fall.py` — detector de caidas standalone (copia propia, no importa de `detectors/`)
- `detectors/` — clases reusables: `FallDetector`, `EppDetector`, `RescueDetector`
- `backend/` — pipeline serial+deteccion+WebSocket+Supabase (hardware ESP32);
  ver `.claude/skills/ukucha/backend-conexion.md` para la arquitectura completa
- `server.py` — backend FastAPI legado para telemetria de gases y frames
- `requirements.txt` — dependencias pinneadas (exacto match con el venv)
- `env.example` — variables de entorno documentadas (copiar a `.env`)

## Convenciones

- Commits: ver `.claude/skills/commits.md`
- Entorno virtual: SIEMPRE usar `venv\Scripts\python.exe`, nunca python global
- Codigo fuente en ingles (variables, funciones, comentarios)
- Interfaz de usuario (labels en pantalla) en español
- Skills desactualizadas: ver `.claude/skills/skills-sync.md` — antes de
  cambios de dependencias, arquitectura, o variables de entorno, proponer
  (preguntando primero) que skills necesitan actualizarse
