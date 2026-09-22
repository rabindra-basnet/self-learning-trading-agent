"""FastAPI composition root — application factory and startup checks."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from magic_di.fastapi import Provide, inject_app

from app.core.config.settings import get_settings
from app.core.exceptions.taxonomy import FatalSystemError
from app.core.logging.setup import configure_logging, get_logger
from app.di import configure_injector
from app.infrastructure.capability.database import ClickHouseConnection, PostgresConnection
from app.infrastructure.capability.redis import RedisConnection
from app.modules.strategies.application.manager import StrategyManager
from app.modules.strategies.infrastructure.providers.strategies.library import BUILTIN_STRATEGIES
from app.routers import api_router


def create_app() -> FastAPI:
    """Build the application and its composition root.

    The injector owns dependency construction and lifecycle. The application
    lifespan only contains application-specific startup/shutdown work.
    """

    settings = get_settings()
    configure_logging(settings.app_env)
    logger = get_logger("app.main")
    injector = configure_injector()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # magic-di's inject_app() connects the injector before entering this
        # lifespan and disconnects it after it exits.
        postgres = next(iter(injector.get_dependencies_by_interface(PostgresConnection)))
        clickhouse = next(iter(injector.get_dependencies_by_interface(ClickHouseConnection)))
        redis = next(iter(injector.get_dependencies_by_interface(RedisConnection)))

        checks = await asyncio.gather(
            postgres.ping(),
            clickhouse.ping(),
            redis.ping(),
        )
        failed = [name for name, ok in zip(("postgres", "clickhouse", "redis"), checks, strict=True) if not ok]
        if failed:
            # inject_app() owns injector cleanup even when this lifespan
            # raises before yielding, so do not disconnect it twice.
            raise FatalSystemError(f"startup dependency check failed: {', '.join(failed)}")

        manager = next(iter(injector.get_dependencies_by_interface(StrategyManager)))
        for strategy in BUILTIN_STRATEGIES.values():
            await manager.register(strategy)

        logger.info("startup_complete")
        yield
        logger.info("shutdown_complete")

    application = FastAPI(
        title="Trading Agent Engine",
        version="0.1.0",
        lifespan=lifespan,
    )
    application = inject_app(application, injector=injector)
    application.include_router(api_router)

    @application.get("/health", tags=["system"])
    async def health(
        postgres_conn: Provide[PostgresConnection],
        clickhouse_conn: Provide[ClickHouseConnection],
        redis_conn: Provide[RedisConnection],
    ) -> dict[str, Any]:
        postgres, clickhouse, redis = await asyncio.gather(
            postgres_conn.ping(),
            clickhouse_conn.ping(),
            redis_conn.ping(),
        )
        dependencies = {"postgres": postgres, "clickhouse": clickhouse, "redis": redis}
        return {
            "status": "ok" if all(dependencies.values()) else "degraded",
            "app": "trading-agent-engine",
            "dependencies": dependencies,
        }

    return application


app = create_app()
