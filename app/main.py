"""FastAPI composition root — lifespan wiring, health probe."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config.settings import get_settings
from app.core.logging.setup import get_logger
from app.di import build_container, initialize, shutdown
from app.routers import api_router

logger = get_logger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    container = build_container(settings)
    app.state.container = container
    await initialize(container)
    logger.info("startup_complete")
    yield
    await shutdown(container)
    logger.info("shutdown_complete")


app = FastAPI(title="Trading Agent Engine", version="0.1.0", lifespan=lifespan)
app.include_router(api_router)


@app.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    return {"status": "ok", "app": "trading-agent-engine"}