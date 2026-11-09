from fastapi import APIRouter
from app.routers import auth, targets

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(targets.router)
