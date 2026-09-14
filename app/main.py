"""FastAPI app — composition root wiring, lifespan, health probe."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.di import build_container, initialize, shutdown
from app.api.routers import api_router
from app.core.config.settings import get_settings
from app.core.logging.setup import get_logger

logger = get_logger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    container = build_container(settings)
    app.state.container = container
    await initialize(container)
    logger.info("startup_complete", event_bus=settings.event_bus)
    yield
    await shutdown(container)
    logger.info("shutdown_complete")


app = FastAPI(title="Trading Agent Engine", version="0.1.0", lifespan=lifespan)
app.include_router(api_router)


@app.get("/health", tags=["system"])
async def health() -> dict:
    return {"status": "ok", "app": "trading-agent-engine"}
