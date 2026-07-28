from __future__ import annotations

import math
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

import psycopg


@dataclass(frozen=True)
class CandleBarV2:
    ts: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass(frozen=True)
class CandleRegimeDecisionV2:
    symbol: str
    timeframe: str
    trend: str
    volatility: str
    atr: float
    atr_pct: float
    atr_percentile: float
    adx: float
    normalized_slope: float
    bars: int
    bar_ts: datetime | None
    confirmed_bars: int
    data_ready: bool
    stale: bool
    source_version: str
    reason: str

    @property
    def vol(self) -> str:
        return self.volatility

    @property
    def regime_code(self) -> str:
        if not self.data_ready:
            return "unknown"
        return f"{self.trend}_{self.volatility}"

    def is_tradeable(self) -> bool:
        return self.data_ready and not self.stale and self.confirmed_bars > 0


def _ema(values: list[float], period: int) -> list[float]:
    if not values:
        return []
    alpha = 2.0 / (period + 1.0)
    out = [values[0]]
    for value in values[1:]:
        out.append(alpha * value + (1.0 - alpha) * out[-1])
    return out


def _true_ranges(bars: list[CandleBarV2]) -> list[float]:
    out: list[float] = []
    previous_close: float | None = None
    for bar in bars:
        candidates = [bar.high - bar.low]
        if previous_close is not None:
            candidates.extend((abs(bar.high - previous_close), abs(bar.low - previous_close)))
        out.append(max(candidates))
        previous_close = bar.close
    return out


def _rolling_mean(values: list[float], period: int, index: int) -> float:
    start = max(0, index - period + 1)
    window = values[start : index + 1]
    return sum(window) / len(window) if window else 0.0


def _adx(bars: list[CandleBarV2], period: int, index: int) -> float:
    start = max(1, index - period + 1)
    tr_sum = plus_sum = minus_sum = 0.0
    for idx in range(start, index + 1):
        current, previous = bars[idx], bars[idx - 1]
        tr_sum += max(
            current.high - current.low,
            abs(current.high - previous.close),
            abs(current.low - previous.close),
        )
        up = current.high - previous.high
        down = previous.low - current.low
        plus_sum += up if up > down and up > 0 else 0.0
        minus_sum += down if down > up and down > 0 else 0.0
    if tr_sum <= 0:
        return 0.0
    plus_di = 100.0 * plus_sum / tr_sum
    minus_di = 100.0 * minus_sum / tr_sum
    denominator = plus_di + minus_di
    return 0.0 if denominator <= 0 else 100.0 * abs(plus_di - minus_di) / denominator


def _percentile_rank(history: Iterable[float], value: float) -> float:
    values = [float(item) for item in history if math.isfinite(float(item))]
    if not values:
        return 0.5
    return sum(1 for item in values if item <= value) / len(values)


class CandleRegimeEngineV2:
    """Свечной режим отдельно для каждой связки instrument × timeframe."""

    SOURCE_VERSION = "CANDLE_REGIME_V3"

    def __init__(self, dsn: str | None = None) -> None:
        self.dsn = dsn or os.getenv("DATABASE_URL") or "postgresql:///finam_core"
        self.limit = int(os.getenv("CANDLE_REGIME_HISTORY_BARS", "240"))
        self.atr_period = int(os.getenv("CANDLE_REGIME_ATR_PERIOD", "14"))
        self.fast_period = int(os.getenv("CANDLE_REGIME_EMA_FAST", "20"))
        self.slow_period = int(os.getenv("CANDLE_REGIME_EMA_SLOW", "50"))
        self.adx_period = int(os.getenv("CANDLE_REGIME_ADX_PERIOD", "14"))
        self.adx_min = float(os.getenv("CANDLE_REGIME_ADX_MIN", "18"))
        self.confirm_bars = int(os.getenv("CANDLE_REGIME_CONFIRM_BARS", "3"))
        self.high_percentile = float(os.getenv("CANDLE_REGIME_HIGH_PERCENTILE", "0.75"))
        self.low_percentile = float(os.getenv("CANDLE_REGIME_LOW_PERCENTILE", "0.25"))
        self.cache_ttl = float(os.getenv("CANDLE_REGIME_CACHE_SECONDS", "15"))
        self._cache: dict[tuple[str, str], tuple[float, CandleRegimeDecisionV2]] = {}

    @staticmethod
    def _timeframe_seconds(timeframe: str) -> int:
        return {"M1": 60, "M5": 300, "M15": 900, "H1": 3600}.get(timeframe.upper(), 300)

    def load_bars(self, symbol: str, timeframe: str) -> list[CandleBarV2]:
        timeframe_seconds = self._timeframe_seconds(timeframe)
        with psycopg.connect(self.dsn) as connection:
            rows = connection.execute(
                """
                SELECT ts,open,high,low,close,volume
                FROM market_bars
                WHERE symbol=%s AND timeframe=%s
                  AND ts < date_bin(
                      make_interval(secs => %s),
                      clock_timestamp(),
                      timestamptz '1970-01-01 00:00:00+00'
                  )
                ORDER BY ts DESC
                LIMIT %s
                """,
                (symbol, timeframe, timeframe_seconds, self.limit),
            ).fetchall()
        return [
            CandleBarV2(row[0], *(float(value) for value in row[1:]))
            for row in reversed(rows)
        ]

    def evaluate(self, symbol: str, timeframe: str = "M5") -> CandleRegimeDecisionV2:
        key = (str(symbol), str(timeframe).upper())
        cached = self._cache.get(key)
        now = time.monotonic()
        if cached and now - cached[0] < self.cache_ttl:
            return cached[1]
        decision = self.classify(key[0], key[1], self.load_bars(*key))
        self._cache[key] = (now, decision)
        return decision

    def classify(
        self,
        symbol: str,
        timeframe: str,
        bars: list[CandleBarV2],
        *,
        now: datetime | None = None,
    ) -> CandleRegimeDecisionV2:
        minimum = max(self.slow_period + self.confirm_bars, self.atr_period * 3)
        if len(bars) < minimum:
            return CandleRegimeDecisionV2(
                symbol, timeframe, "unknown", "unknown", 0.0, 0.0, 0.0, 0.0, 0.0,
                len(bars), bars[-1].ts if bars else None, 0, False, True,
                self.SOURCE_VERSION, "insufficient_closed_bars",
            )

        closes = [bar.close for bar in bars]
        tr = _true_ranges(bars)
        ema_fast = _ema(closes, self.fast_period)
        ema_slow = _ema(closes, self.slow_period)
        atr_pct_series = [
            (_rolling_mean(tr, self.atr_period, idx) / closes[idx]) if closes[idx] > 0 else 0.0
            for idx in range(len(bars))
        ]

        raw: list[tuple[str, str, float, float, float, float]] = []
        for idx in range(len(bars) - self.confirm_bars, len(bars)):
            atr = _rolling_mean(tr, self.atr_period, idx)
            atr_pct = atr_pct_series[idx]
            history = atr_pct_series[max(0, idx - 120) : idx]
            percentile = _percentile_rank(history, atr_pct)
            adx = _adx(bars, self.adx_period, idx)
            slope_lookback = min(3, idx)
            slope = (
                (ema_fast[idx] - ema_fast[idx - slope_lookback]) / max(atr, 1e-12)
                if slope_lookback else 0.0
            )
            if adx >= self.adx_min and ema_fast[idx] > ema_slow[idx] and slope > 0.10:
                trend = "trend_up"
            elif adx >= self.adx_min and ema_fast[idx] < ema_slow[idx] and slope < -0.10:
                trend = "trend_down"
            else:
                trend = "range"
            volatility = "high_vol" if percentile >= self.high_percentile else (
                "low_vol" if percentile <= self.low_percentile else "normal_vol"
            )
            raw.append((trend, volatility, atr, atr_pct, percentile, adx))

        confirmed = len({(row[0], row[1]) for row in raw}) == 1
        trend, volatility, atr, atr_pct, percentile, adx = raw[-1]
        if not confirmed:
            # Не подменяем неопределённый режим безопасно выглядящим боковиком.
            # До подтверждения несколькими закрытыми барами новый вход запрещён.
            trend, volatility = "unknown", "unknown"

        now = now or datetime.now(timezone.utc)
        bar_ts = bars[-1].ts
        if bar_ts.tzinfo is None:
            bar_ts = bar_ts.replace(tzinfo=timezone.utc)
        stale_after = self._timeframe_seconds(timeframe) * 3
        stale = (now.astimezone(timezone.utc) - bar_ts.astimezone(timezone.utc)).total_seconds() > stale_after
        slope = (ema_fast[-1] - ema_fast[-4]) / max(atr, 1e-12)
        reason = (
            f"closed_bars={len(bars)} atr_pct={atr_pct:.6f} percentile={percentile:.3f} "
            f"adx={adx:.2f} slope_atr={slope:.3f} confirmed={int(confirmed)} stale={int(stale)}"
        )
        return CandleRegimeDecisionV2(
            symbol, timeframe, trend, volatility, atr, atr_pct, percentile, adx, slope,
            len(bars), bar_ts, self.confirm_bars if confirmed else 0, confirmed, stale,
            self.SOURCE_VERSION, reason,
        )
