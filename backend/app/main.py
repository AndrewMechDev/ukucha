from fastapi import FastAPI

from app.api.v1 import v1_router

app = FastAPI(title="Ukucha API", version="0.1.0")
app.include_router(v1_router, prefix="/api")


@app.get("/")
async def root():
    return {"message": "Ukucha API v0.1.0"}
