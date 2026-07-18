from fastapi import APIRouter

from app.api.v1.endpoints import router as endpoints_router

v1_router = APIRouter(prefix="/v1")
v1_router.include_router(endpoints_router)
