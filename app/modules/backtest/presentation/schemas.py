from pydantic import BaseModel

from app.modules.backtest.domain.entities import BacktestResult


class BacktestRunRequest(BaseModel):
    symbol: str = "BTC/USDT"
    timeframe: str = "1h"
    strategy_id: str
    start: str
    end: str
    initial_capital: str = "10000"
    fee_pct: str = "0.001"
    seed: int | None = None
    folds: int | None = None


class BacktestRunResponse(BaseModel):
    results: list[BacktestResult]
