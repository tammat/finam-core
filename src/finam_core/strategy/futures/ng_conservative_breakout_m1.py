from __future__ import annotations

from finam_core.strategy.futures.ng_conservative_breakout import (
    NgBreakoutSignal,
    NgConservativeBreakout,
)


class NgConservativeBreakoutM1(NgConservativeBreakout):
    """Русский комментарий: M1-профиль breakout-стратегии для NG."""

    def __init__(self, *, symbol: str) -> None:
        super().__init__(
            symbol=symbol,
            timeframe="M1",
            lookback=40,
            atr_window=20,
            min_atr_ratio=0.0008,
            stop_atr=0.8,
            take_atr=1.6,
        )
