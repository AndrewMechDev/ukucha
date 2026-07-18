# ukucha

Monorepo del proyecto Ukucha.

**Python**: 3.12.10 | **Node**: 24+

## Estructura

```
ukucha/
├── backend/          # Backend v2: enlace serial + deteccion + WebSocket + Supabase
│   ├── schemas/      # Pydantic: paquetes uplink/downlink, salida enriquecida
│   ├── ports/        # Protocols (Transport, PersistenceBackend) — Ports & Adapters
│   ├── adapters/      # Implementaciones: serial/mock, supabase/null
│   ├── services/      # SerialManager, FrameReassembler, DetectionService, etc.
│   ├── api/           # WebSocket /ws/stream, /ws/commands + REST
│   └── app.py         # ensamblado FastAPI (create_app)
├── detectors/        # FallDetector, EppDetector, RescueDetector (reusados por backend/ y ukucha_detector.py)
├── models/           # Pesos YOLO/DRespNet pre-entrenados (yolov8n.pt, epp_yolo8m.pt, drespnet_best.pt)
├── ukucha_detector.py # Pipeline unificado webcam (3 detectores + fusion) — fuente de verdad de la fusion
├── webcam_fall.py     # Detector de caidas standalone (demo)
├── server.py          # Backend FastAPI legado (telemetria de gases, ver .claude/skills/ukucha/server.md)
├── frontend/         # React + Vite (TypeScript)
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   └── services/
│   └── public/
├── .claude/skills/   # Skills del proyecto (arquitectura, convenciones — ver CLAUDE.md)
├── requirements.txt  # Dependencias Python (deteccion + backend, pinneadas)
├── env.example       # Variables de entorno documentadas (copiar a .env)
├── .python-version   # Python 3.12.10
└── README.md
```

Ver `CLAUDE.md` y `.claude/skills/ukucha/` para el detalle completo de arquitectura,
decisiones de diseño y como regenerar cada modulo.

## Inicio rápido

### Backend

```bash
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# Modo mock (default, sin hardware ni Supabase)
uvicorn backend.app:app --host 0.0.0.0 --port 8000
```

Sin variables de entorno, arranca con `MockTransport` (trafico sintetico) y
`NullPersistenceAdapter` (no persiste nada). Para hardware real y Supabase,
copiar `env.example` a `.env` y completar — ver
`.claude/skills/ukucha/backend-conexion.md`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

El frontend corre en `http://localhost:5173` y el proxy de Vite redirige `/api/*` al backend en `http://localhost:8000`.
