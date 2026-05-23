from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NgBreakoutSignal:
    symbol: str
    side: str
    strategy: str
    timeframe: str
    reason: str
    entry_price: float
    stop_price: float
    take_price: float
    confidence: float


class NgConservativeBreakout:
    """
    Русский комментарий:
    Консервативная breakout-стратегия для фьючерсов NG.
    Стратегия только формирует сигнал, заявки не отправляет.
    """

    def __init__(
        self,
        *,
        symbol: str,
        timeframe: str = "M5",
        lookback: int = 20,
        atr_window: int = 14,
        min_atr_ratio: float = 0.0015,
        stop_atr: float = 1.0,
        take_atr: float = 2.0,
    ) -> None:
        self.symbol = symbol
        self.timeframe = timeframe
        self.lookback = lookback
        self.atr_window = atr_window
        self.min_atr_ratio = min_atr_ratio
        self.stop_atr = stop_atr
        self.take_atr = take_atr

    def on_bars(self, bars: list[dict]) -> NgBreakoutSignal | None:
        if len(bars) < max(self.lookback, self.atr_window) + 2:
            return None

        recent = bars[-self.lookback - 1:-1]
        last = bars[-1]

        highs = [float(x["high"]) for x in recent]
        lows = [float(x["low"]) for x in recent]

        range_high = max(highs)
        range_low = min(lows)

        close = float(last["close"])
        high = float(last["high"])
        low = float(last["low"])

        atr = self._atr(bars[-self.atr_window - 1:])
        if close <= 0:
            return None

        atr_ratio = atr / close
        if atr_ratio < self.min_atr_ratio:
            return None

        if close > range_high and high > range_high:
            return NgBreakoutSignal(
                symbol=self.symbol,
                side="BUY",
                strategy="NG_CONSERVATIVE_BREAKOUT",
                timeframe=self.timeframe,
                reason=f"ng_breakout_up range_high={round(range_high, 6)} atr_ratio={round(atr_ratio, 6)}",
                entry_price=close,
                stop_price=round(close - self.stop_atr * atr, 6),
                take_price=round(close + self.take_atr * atr, 6),
                confidence=min(1.0, atr_ratio / self.min_atr_ratio),
            )

        if close < range_low and low < range_low:
            return NgBreakoutSignal(
                symbol=self.symbol,
                side="SELL",
                strategy="NG_CONSERVATIVE_BREAKOUT",
                timeframe=self.timeframe,
                reason=f"ng_breakout_down range_low={round(range_low, 6)} atr_ratio={round(atr_ratio, 6)}",
                entry_price=close,
                stop_price=round(close + self.stop_atr * atr, 6),
                take_price=round(close - self.take_atr * atr, 6),
                confidence=min(1.0, atr_ratio / self.min_atr_ratio),
            )

        return None

    def _atr(self, bars: list[dict]) -> float:
        ranges = []
        for prev, cur in zip(bars, bars[1:]):
            high = float(cur["high"])
            low = float(cur["low"])
            prev_close = float(prev["close"])
            ranges.append(
                max(
                    high - low,
                    abs(high - prev_close),
                    abs(low - prev_close),
                )
            )

        if not ranges:
            return 0.0

        return sum(ranges) / len(ranges)
