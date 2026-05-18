from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RegimeInput:
    symbol: str
    close: float
    prev_close: float
    high: float
    low: float
    open: float
    avg_range_pct: float


@dataclass(frozen=True)
class ResearchRegime:
    symbol: str
    trend: str
    volatility: str
    regime: str
    reason: str


class ResearchRegimeClassifier:
    """Русский комментарий: классифицирует рыночный режим по свечным признакам для research layer."""

    def classify(self, item: RegimeInput) -> ResearchRegime:
        close = float(item.close)
        prev_close = float(item.prev_close)
        open_price = float(item.open)
        high = float(item.high)
        low = float(item.low)

        if prev_close <= 0 or open_price <= 0:
            return ResearchRegime(
                symbol=item.symbol,
                trend="unknown",
                volatility="unknown",
                regime="UNKNOWN",
                reason="некорректные_цены",
            )

        ret_pct = (close - prev_close) / prev_close
        candle_body_pct = (close - open_price) / open_price
        range_pct = (high - low) / open_price if open_price else 0.0

        avg_range_pct = max(float(item.avg_range_pct or 0.0), 1e-9)

        if abs(ret_pct) >= 0.035 or range_pct >= avg_range_pct * 2.5:
            volatility = "high_vol"
        elif range_pct <= avg_range_pct * 0.6:
            volatility = "low_vol"
        else:
            volatility = "normal_vol"

        if candle_body_pct >= 0.015 and ret_pct > 0:
            trend = "trend_up"
        elif candle_body_pct <= -0.015 and ret_pct < 0:
            trend = "trend_down"
        elif range_pct <= avg_range_pct * 0.75:
            trend = "squeeze"
        else:
            trend = "range"

        regime = f"{trend}:{volatility}"

        return ResearchRegime(
            symbol=item.symbol,
            trend=trend,
            volatility=volatility,
            regime=regime,
            reason=(
                f"ret_pct={ret_pct:.6f};"
                f"body_pct={candle_body_pct:.6f};"
                f"range_pct={range_pct:.6f};"
                f"avg_range_pct={avg_range_pct:.6f}"
            ),
        )
