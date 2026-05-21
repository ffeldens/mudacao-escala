"""Entry point do FastAPI."""

from __future__ import annotations

import logging
import traceback
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from escala_freemium_api import __version__
from escala_freemium_api.config import get_settings
from escala_freemium_api.db import init_db
from escala_freemium_api.routes import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Cria tabelas no startup. Em prod, considerar migrations explícitas."""
    logger.info("Inicializando DB (schema=%s)", get_settings().DB_SCHEMA)
    init_db()
    logger.info("DB pronto. App rodando v%s", __version__)
    yield
    logger.info("App finalizando.")


settings = get_settings()

app = FastAPI(
    title="MudAção Escala — API freemium",
    version=__version__,
    description="Simulador PEC 8/2025 — captura de leads + simulação 6x1 → 5x2",
    lifespan=lifespan,
)

# CORS: em dev permite localhost:3000; em prod restringe ao próprio domínio.
_allowed_origins = (
    [settings.APP_BASE_URL]
    if settings.is_production
    else ["http://localhost:3000", "http://127.0.0.1:3000"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(router)


# Em dev, devolve traceback completo no body pra debug mais rápido.
@app.exception_handler(Exception)
async def debug_exception_handler(request: Request, exc: Exception):
    tb = traceback.format_exc()
    logger.error("Unhandled exception on %s %s:\n%s", request.method, request.url.path, tb)
    if settings.is_production:
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})
    return JSONResponse(
        status_code=500,
        content={
            "detail": f"{type(exc).__name__}: {exc}",
            "traceback": tb.splitlines()[-15:],  # últimas 15 linhas
            "path": str(request.url.path),
        },
    )


@app.get("/", tags=["meta"])
async def root():
    return {
        "app": "MudAção Escala — API freemium",
        "version": __version__,
        "docs": "/docs",
    }
