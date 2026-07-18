# ukucha

Monorepo del proyecto Ukucha.

**Python**: 3.12.10 | **Node**: 24+

## Estructura

```
ukucha/
├── backend/          # FastAPI (Python)
│   ├── app/
│   │   ├── api/      # Rutas y endpoints
│   │   ├── core/     # Configuración
│   │   ├── models/   # Modelos SQLAlchemy
│   │   ├── schemas/  # Esquemas Pydantic
│   │   ├── services/ # Lógica de negocio
│   │   └── db/       # Conexión a base de datos
│   └── tests/
├── frontend/         # React + Vite (TypeScript)
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   └── services/
│   └── public/
├── .python-version   # Python 3.12.10
└── README.md
```

## Inicio rápido

### Backend

```bash
cd backend
py -3.12 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

El frontend corre en `http://localhost:5173` y el proxy de Vite redirige `/api/*` al backend en `http://localhost:8000`.
