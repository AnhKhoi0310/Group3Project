from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.auth import get_token_verifier
from app.config import CorsSettings, get_settings
from app.errors import ApiError, handle_api_error, handle_validation_error
from app.routers import auth, ingestions, targets


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    # Refuse to start with missing or invalid configuration.
    get_settings()
    get_token_verifier()
    yield


app = FastAPI(title="ReviewLens API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CorsSettings().origins,
    allow_methods=["*"],
    allow_headers=["Authorization", "Content-Type"],
)
app.add_exception_handler(ApiError, handle_api_error)
app.add_exception_handler(RequestValidationError, handle_validation_error)
app.include_router(auth.router)
app.include_router(targets.router)
app.include_router(ingestions.router)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
