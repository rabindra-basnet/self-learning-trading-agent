"""Cross-slice contract models — normalized market data shared by other slices.

Slices ONLY depend on this package (plus core); never on marketdata internals.
"""

from app.modules.marketdata.domain.entities import Candle, Symbol, Timeframe
from app.modules.marketdata.domain.events import CandleReceived

__all__ = ["Candle", "CandleReceived", "Symbol", "Timeframe"]
