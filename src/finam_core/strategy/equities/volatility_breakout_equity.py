from __future__ import annotations

from collections import deque
from dataclasses import dataclass

from finam_core.signals.signal_intent import SignalIntent


@dataclass
class VolatilityBreakoutConfig:
    lookback: int = 20
    min_atr_pct: float = 0.008
    volume_mult: float = 1.5
    stop_atr: float = 1.2
    take_atr: float = 2.0
    qty: float = 1.0
    allow_long: bool = True
    allow_short: bool = True


class VolatilityBreakoutEquity:
    """
    Русский комментарий:
    Стратегия для самых волатильных акций:
    вход только при пробое диапазона с подтверждением объёмом.
    """

    name = "VOLATILITY_BREAKOUT_EQUITY"

    def __init__(self, config: VolatilityBreakoutConfig | None = None) -> None:
        self.config = config or VolatilityBreakoutConfig()
        self.highs: deque[float] = deque(maxlen=self.config.lookback)
        self.lows: deque[float] = deque(maxlen=self.config.lookback)
        self.volumes: deque[float] = deque(maxlen=self.config.lookback)

    def on_quote(
        self,
        symbol: str,
        price: float,
        high: float | None = None,
        volume: float | None = None,
        atr: float | None = None,
        regime: str | None = None,
    ) -> SignalIntent | None:
        price = float(price)
        high = float(high if high is not None else price)
        volume = float(volume or 0.0)
        atr = float(atr or 0.0)

        if len(self.highs) < self.config.lookback:
            self.highs.append(high)
            self.lows.append(price)
            self.volumes.append(volume)
            return None

        range_high = max(self.highs)
        range_low = min(self.lows)
        avg_volume = sum(self.volumes) / max(len(self.volumes), 1)
        atr_pct = atr / price if price > 0 else 0.0

        self.highs.append(high)
        self.lows.append(price)
        self.volumes.append(volume)

        if atr_pct < self.config.min_atr_pct:
            return None

        if avg_volume > 0 and volume < avg_volume * self.config.volume_mult:
            return None

        regime_code = str(regime or "").lower()
        long_allowed_by_regime = not regime_code.startswith("trend_down")
        short_allowed_by_regime = not regime_code.startswith("trend_up")

        if self.config.allow_long and long_allowed_by_regime and price > range_high:
            side = "BUY"
            stop = price - atr * self.config.stop_atr
            take = price + atr * self.config.take_atr
            reason = "range_breakout_up_with_volume"
        elif self.config.allow_short and short_allowed_by_regime and price < range_low:
            side = "SELL"
            stop = price + atr * self.config.stop_atr
            take = price - atr * self.config.take_atr
            reason = "range_breakout_down_with_volume"
        else:
            return None

        return SignalIntent(
            symbol=symbol,
            side=side,
            strategy=self.name,
            qty=self.config.qty,
            entry_price=price,
            stop_price=round(stop, 6),
            take_profit=round(take, 6),
            confidence=0.7,
            timeframe="LIVE",
            horizon="INTRADAY",
            regime=regime,
            source="volatility_breakout_equity",
            reason=reason,
            features={
                "range_high": range_high,
                "range_low": range_low,
                "atr": atr,
                "atr_pct": atr_pct,
                "volume": volume,
                "avg_volume": avg_volume,
                "volume_mult": self.config.volume_mult,
                "setup_type": "volatility_breakout",
            },
        )
