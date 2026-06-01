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

    def on_signal_bar(self, *args, **kwargs):
        """Совместимость с MTF pipeline.

        Русский комментарий: pipeline может передавать либо один объект bar,
        либо именованные поля ts/open/high/low/close/volume. Здесь нормализуем
        оба варианта и передаём дальше в существующую логику стратегии.
        """
        bar = args[0] if args else kwargs

        if hasattr(self, "on_bar"):
            return self.on_bar(bar)
        if hasattr(self, "on_market_bar"):
            return self.on_market_bar(bar)
        if hasattr(self, "generate_signal"):
            return self.generate_signal(bar)
        if hasattr(self, "on_bars"):
            return self.on_bars([bar])
        return None

