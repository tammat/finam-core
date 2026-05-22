from __future__ import annotations

import statistics
from dataclasses import dataclass

import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url
from finam_core.analytics.regime_snapshot_repository import RegimeSnapshotRepository


@dataclass(frozen=True)
class FuturesRegimeState:
    symbol: str
    timeframe: str
    regime: str
    trend: str
    volatility: str
    atr: float
    bars: int
    reason: str


class FuturesRegimeEngine:
    """
    Русский комментарий:
    Расчётный regime engine для фьючерсов.
    v1 использует market_bars: close/high/low и простые устойчивые эвристики.
    """

    def __init__(self, dsn: str | None = None) -> None:
        self.dsn = dsn or build_psycopg_url()

    def load_bars(self, *, symbol: str, timeframe: str, limit: int = 120) -> list[tuple[float, float, float]]:
        sql = """
        SELECT high, low, close
        FROM market_bars
        WHERE symbol = %s
          AND timeframe = %s
        ORDER BY ts DESC
        LIMIT %s
        """

        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (symbol, timeframe, limit))
                rows = cur.fetchall()

        rows = list(reversed(rows))
        return [(float(h), float(l), float(c)) for h, l, c in rows if h is not None and l is not None and c is not None]

    def calculate(self, *, symbol: str, timeframe: str = "M5") -> FuturesRegimeState:
        bars = self.load_bars(symbol=symbol, timeframe=timeframe)

        if len(bars) < 20:
            return FuturesRegimeState(
                symbol=symbol,
                timeframe=timeframe,
                regime="unknown",
                trend="unknown",
                volatility="unknown",
                atr=0.0,
                bars=len(bars),
                reason="insufficient_bars",
            )

        closes = [x[2] for x in bars]
        ranges = [max(h - l, 0.0) for h, l, _ in bars]

        atr = statistics.mean(ranges[-14:]) if len(ranges) >= 14 else statistics.mean(ranges)
        avg_close = statistics.mean(closes[-20:])

        if avg_close <= 0:
            return FuturesRegimeState(
                symbol=symbol,
                timeframe=timeframe,
                regime="unknown",
                trend="unknown",
                volatility="unknown",
                atr=atr,
                bars=len(bars),
                reason="bad_avg_close",
            )

        trend_gap = (closes[-1] - closes[-20]) / avg_close
        atr_ratio = atr / avg_close

        if trend_gap > 0.003:
            trend = "up"
        elif trend_gap < -0.003:
            trend = "down"
        else:
            trend = "flat"

        if atr_ratio >= 0.01:
            volatility = "high"
        elif atr_ratio >= 0.003:
            volatility = "normal"
        else:
            volatility = "low"

        if trend in ("up", "down") and volatility in ("normal", "high"):
            regime = "trend"
        elif trend == "flat" and volatility == "low":
            regime = "compression"
        else:
            regime = "range"

        return FuturesRegimeState(
            symbol=symbol,
            timeframe=timeframe,
            regime=regime,
            trend=trend,
            volatility=volatility,
            atr=atr,
            bars=len(bars),
            reason=f"trend_gap={round(trend_gap, 6)} atr_ratio={round(atr_ratio, 6)}",
        )

    def calculate_and_save(self, *, symbol: str, timeframe: str = "M5") -> FuturesRegimeState:
        state = self.calculate(symbol=symbol, timeframe=timeframe)

        repo = RegimeSnapshotRepository(self.dsn)
        repo.migrate()
        repo.save_snapshot(
            symbol=symbol,
            timeframe=timeframe,
            regime=state.regime,
            trend=state.trend,
            volatility=state.volatility,
            atr=state.atr,
            source="futures_regime_engine_v1",
        )

        return state
