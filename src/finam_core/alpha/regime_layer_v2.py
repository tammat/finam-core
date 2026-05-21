from __future__ import annotations

from dataclasses import dataclass
from statistics import mean


@dataclass(frozen=True)
class RegimeDecision:
    symbol: str
    trend: str
    volatility: str
    regime: str
    tradable: bool
    confidence: float
    reason: str


class RegimeLayerV2:
    """Русский комментарий: классифицирует рыночный режим по тренду и волатильности."""

    def __init__(
        self,
        *,
        short_window: int = 5,
        long_window: int = 20,
        vol_window: int = 20,
        low_vol_threshold: float = 0.004,
        high_vol_threshold: float = 0.018,
        min_points: int = 25,
    ) -> None:
        self.short_window = short_window
        self.long_window = long_window
        self.vol_window = vol_window
        self.low_vol_threshold = low_vol_threshold
        self.high_vol_threshold = high_vol_threshold
        self.min_points = min_points

    def classify(self, *, symbol: str, prices: list[float]) -> RegimeDecision:
        clean = [float(p) for p in prices if p and float(p) > 0]

        if len(clean) < self.min_points:
            return RegimeDecision(
                symbol=symbol,
                trend="unknown",
                volatility="unknown",
                regime="insufficient_data",
                tradable=False,
                confidence=0.0,
                reason=f"need_at_least_{self.min_points}_prices",
            )

        short_ma = mean(clean[-self.short_window:])
        long_ma = mean(clean[-self.long_window:])

        trend_gap = (short_ma - long_ma) / long_ma if long_ma else 0.0

        if trend_gap > 0.003:
            trend = "up"
        elif trend_gap < -0.003:
            trend = "down"
        else:
            trend = "flat"

        returns = []
        recent = clean[-self.vol_window - 1 :]
        for prev, cur in zip(recent, recent[1:]):
            if prev > 0:
                returns.append(abs((cur - prev) / prev))

        avg_abs_return = mean(returns) if returns else 0.0

        if avg_abs_return < self.low_vol_threshold:
            volatility = "low"
        elif avg_abs_return > self.high_vol_threshold:
            volatility = "high"
        else:
            volatility = "normal"

        if trend == "up" and volatility in {"normal", "low"}:
            regime = "trend_up"
            tradable = True
        elif trend == "down" and volatility == "high":
            regime = "risk_off"
            tradable = False
        elif trend == "down":
            regime = "trend_down"
            tradable = True
        elif trend == "flat" and volatility == "low":
            regime = "compression"
            tradable = False
        elif trend == "flat" and volatility == "high":
            regime = "chaos"
            tradable = False
        else:
            regime = "range"
            tradable = True

        confidence = min(1.0, abs(trend_gap) * 100 + avg_abs_return * 20)

        return RegimeDecision(
            symbol=symbol,
            trend=trend,
            volatility=volatility,
            regime=regime,
            tradable=tradable,
            confidence=round(confidence, 4),
            reason=f"trend_gap={round(trend_gap, 6)} avg_abs_return={round(avg_abs_return, 6)}",
        )
