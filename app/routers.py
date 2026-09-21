"""Router aggregation — imports slice routers directly."""

from fastapi import APIRouter

from app.modules.auth.presentation.routes import router as auth_router
from app.modules.backtest.presentation.routes import router as backtest_router
from app.modules.marketdata.presentation.routes import router as marketdata_router
from app.modules.risk.presentation.routes import router as risk_router
from app.modules.signals.presentation.routes import router as signals_router
from app.modules.strategies.presentation.routes import router as strategies_router
from app.modules.trading.presentation.routes import router as trading_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(marketdata_router)
api_router.include_router(signals_router)
api_router.include_router(strategies_router)
api_router.include_router(backtest_router)
api_router.include_router(risk_router)
api_router.include_router(trading_router)
