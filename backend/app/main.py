from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.routers import (
    auth,
    bordereau,
    cable_book,
    caneco,
    cps,
    field_entry,
    projects,
    public,
    tableau,
    verification,
)
from app.core.config import settings
from app.core.logging import configure_logging
from app.core.ratelimit import limiter

configure_logging()

app = FastAPI(
    title="Valorisation des données CANECO BT",
    description="API du projet Challenge Innovation VEAO 2026 — Actemium Cegelec / VINCI Energies",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(caneco.router)
app.include_router(bordereau.router)
app.include_router(cps.router)
app.include_router(verification.router)
app.include_router(cable_book.router)
app.include_router(tableau.router)
app.include_router(field_entry.router)
app.include_router(public.router)


@app.get("/api/health", tags=["system"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}
