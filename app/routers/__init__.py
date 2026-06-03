from fastapi import APIRouter
from app.routers.terminology import router as terminology_router

api_router = APIRouter()
api_router.include_router(terminology_router, prefix="/terminology", tags=["Terminology"])
