"""FastAPI composition root — lifespan wiring, health probe."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any, cast

from fastapi import FastAPI, Request

from app.core.config.settings import get_settings
from app.core.container import Container
from app.core.logging.setup import get_logger
from app.di import build_container, initialize, shutdown
from app.infrastructure.capability.database import ClickHouseConnection, PostgresConnection
from app.infrastructure.capability.redis import RedisConnection
from app.routers import api_router

logger = get_logger("app.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    container = build_container(settings)
    app.state.container = container
    try:
        await initialize(container)
    except Exception:
        await shutdown(container)
        raise
    logger.info("startup_complete")
    yield
    await shutdown(container)
    logger.info("shutdown_complete")


app = FastAPI(title="Trading Agent Engine", version="0.1.0", lifespan=lifespan)
app.include_router(api_router)


@app.get("/health", tags=["system"])
async def health(request: Request) -> dict[str, Any]:
    container = cast("Container", request.app.state.container)
    postgres, clickhouse, redis = await asyncio.gather(
        container.resolve(PostgresConnection).ping(),
        container.resolve(ClickHouseConnection).ping(),
        container.resolve(RedisConnection).ping(),
    )
    dependencies = {"postgres": postgres, "clickhouse": clickhouse, "redis": redis}
    return {
        "status": "ok" if all(dependencies.values()) else "degraded",
        "app": "trading-agent-engine",
        "dependencies": dependencies,
    }
