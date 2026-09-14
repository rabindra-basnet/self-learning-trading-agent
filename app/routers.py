"""Router aggregation — imports slice routers directly, no re-export indirection."""

from fastapi import APIRouter

from app.modules.auth.api.routes import router as auth_router
from app.modules.backtest.api.routes import router as backtest_router
from app.modules.marketdata.api.routes import router as marketdata_router
from app.modules.risk.api.routes import router as risk_router
from app.modules.signals.api.routes import router as signals_router
from app.modules.strategies.api.routes import router as strategies_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(marketdata_router)
api_router.include_router(signals_router)
api_router.include_router(strategies_router)
api_router.include_router(backtest_router)
api_router.include_router(risk_router)
