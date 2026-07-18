# ukucha

Monorepo del proyecto Ukucha.

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
└── README.md
```

## Inicio rápido

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```
