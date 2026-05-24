from __future__ import annotations

import argparse
import math
from dataclasses import dataclass

import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url


@dataclass(frozen=True)
class Bar:
    ts: object
    open: float
    high: float
    low: float
    close: float
    volume: float


def safe_float(v, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def calc_radar_features(bars: list[Bar]) -> dict[str, float | str]:
    """
    Русский комментарий:
    Считает рыночные признаки для radar-кандидата.
    Никаких торговых решений здесь нет.
    """
    if len(bars) < 40:
        return {
            "trend_score": 0.0,
            "volatility_score": 0.0,
            "compression_score": 0.0,
            "breakout_score": 0.0,
            "liquidity_score": 0.0,
            "edge_score": 0.0,
            "regime_hint": "INSUFFICIENT_DATA",
        }

    closes = [b.close for b in bars]
    highs = [b.high for b in bars]
    lows = [b.low for b in bars]
    volumes = [b.volume for b in bars]

    close = closes[-1]

    short_window = 20
    long_window = 60 if len(bars) >= 60 else 40

    short_avg = sum(closes[-short_window:]) / short_window
    long_avg = sum(closes[-long_window:]) / long_window

    trend_raw = abs(short_avg - long_avg) / close if close else 0.0
    trend_score = clamp(trend_raw / 0.01)

    ranges = [max(0.0, h - l) for h, l in zip(highs, lows)]
    recent_range = sum(ranges[-20:]) / 20
    previous_range = sum(ranges[-40:-20]) / 20 if len(ranges) >= 40 else recent_range

    volatility_expansion = recent_range / previous_range if previous_range else 1.0
    volatility_score = clamp((volatility_expansion - 1.0) / 1.5)

    local_range = max(highs[-20:]) - min(lows[-20:])
    compression_score = 1.0 - clamp((local_range / close) / 0.015) if close else 0.0

    prior_high = max(highs[-21:-1])
    prior_low = min(lows[-21:-1])
    breakout_up = max(0.0, close - prior_high)
    breakout_down = max(0.0, prior_low - close)
    breakout_raw = max(breakout_up, breakout_down) / recent_range if recent_range else 0.0
    breakout_score = clamp(breakout_raw)

    recent_volume = sum(volumes[-20:]) / 20
    previous_volume = sum(volumes[-40:-20]) / 20 if len(volumes) >= 40 else recent_volume
    volume_expansion = recent_volume / previous_volume if previous_volume else 1.0
    liquidity_score = clamp((volume_expansion - 1.0) / 2.0)

    edge_score = (
        0.30 * trend_score
        + 0.25 * volatility_score
        + 0.20 * breakout_score
        + 0.15 * compression_score
        + 0.10 * liquidity_score
    )

    if breakout_score >= 0.6 and volatility_score >= 0.4:
        regime_hint = "BREAKOUT_EXPANSION"
    elif compression_score >= 0.7:
        regime_hint = "COMPRESSION"
    elif trend_score >= 0.5:
        regime_hint = "TREND"
    elif volatility_score >= 0.5:
        regime_hint = "VOLATILITY_EXPANSION"
    else:
        regime_hint = "NEUTRAL"

    return {
        "trend_score": round(trend_score, 6),
        "volatility_score": round(volatility_score, 6),
        "compression_score": round(compression_score, 6),
        "breakout_score": round(breakout_score, 6),
        "liquidity_score": round(liquidity_score, 6),
        "edge_score": round(edge_score, 6),
        "regime_hint": regime_hint,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit-bars", type=int, default=120)
    args = parser.parse_args()

    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS market_radar_candidates (
                    id BIGSERIAL PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    asset_group TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    trend_score NUMERIC NOT NULL,
                    volatility_score NUMERIC NOT NULL,
                    compression_score NUMERIC NOT NULL,
                    breakout_score NUMERIC NOT NULL,
                    liquidity_score NUMERIC NOT NULL,
                    edge_score NUMERIC NOT NULL,
                    candidate_rank INTEGER NOT NULL,
                    regime_hint TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    calculated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    UNIQUE(symbol, timeframe)
                );

                CREATE INDEX IF NOT EXISTS idx_market_radar_candidates_rank
                ON market_radar_candidates(candidate_rank, edge_score DESC);

                CREATE INDEX IF NOT EXISTS idx_market_radar_candidates_symbol
                ON market_radar_candidates(symbol, timeframe);
            """)

            cur.execute("""
                SELECT symbol, asset_group, timeframe
                FROM market_data_watch_universe
                WHERE is_enabled = true
                ORDER BY asset_group, symbol
            """)
            watch_items = cur.fetchall()

            scored = []

            for symbol, asset_group, timeframe in watch_items:
                cur.execute("""
                    SELECT ts, open, high, low, close, volume
                    FROM market_bars
                    WHERE symbol=%s
                      AND timeframe=%s
                    ORDER BY ts DESC
                    LIMIT %s
                """, (symbol, timeframe, args.limit_bars))

                rows = cur.fetchall()
                bars = [
                    Bar(
                        ts=r[0],
                        open=safe_float(r[1]),
                        high=safe_float(r[2]),
                        low=safe_float(r[3]),
                        close=safe_float(r[4]),
                        volume=safe_float(r[5]),
                    )
                    for r in reversed(rows)
                ]

                features = calc_radar_features(bars)
                scored.append((symbol, asset_group, timeframe, features, len(bars)))

            scored.sort(key=lambda x: float(x[3]["edge_score"]), reverse=True)

            saved = 0
            for rank, (symbol, asset_group, timeframe, features, bars_count) in enumerate(scored, start=1):
                reason = (
                    f"bars={bars_count} regime={features['regime_hint']} "
                    f"trend={features['trend_score']} vol={features['volatility_score']} "
                    f"compression={features['compression_score']} breakout={features['breakout_score']} "
                    f"liquidity={features['liquidity_score']}"
                )

                cur.execute("""
                    INSERT INTO market_radar_candidates (
                        symbol, asset_group, timeframe,
                        trend_score, volatility_score, compression_score,
                        breakout_score, liquidity_score, edge_score,
                        candidate_rank, regime_hint, reason, calculated_at
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now())
                    ON CONFLICT(symbol, timeframe)
                    DO UPDATE SET
                        asset_group=EXCLUDED.asset_group,
                        trend_score=EXCLUDED.trend_score,
                        volatility_score=EXCLUDED.volatility_score,
                        compression_score=EXCLUDED.compression_score,
                        breakout_score=EXCLUDED.breakout_score,
                        liquidity_score=EXCLUDED.liquidity_score,
                        edge_score=EXCLUDED.edge_score,
                        candidate_rank=EXCLUDED.candidate_rank,
                        regime_hint=EXCLUDED.regime_hint,
                        reason=EXCLUDED.reason,
                        calculated_at=now()
                """, (
                    symbol,
                    asset_group,
                    timeframe,
                    features["trend_score"],
                    features["volatility_score"],
                    features["compression_score"],
                    features["breakout_score"],
                    features["liquidity_score"],
                    features["edge_score"],
                    rank,
                    features["regime_hint"],
                    reason,
                ))

                print(
                    "MARKET_RADAR_CANDIDATE "
                    f"rank={rank} symbol={symbol} timeframe={timeframe} "
                    f"asset_group={asset_group} edge={features['edge_score']} "
                    f"regime={features['regime_hint']} reason={reason}",
                    flush=True,
                )
                saved += 1

        conn.commit()

    print(f"MARKET_RADAR_CANDIDATES_SUMMARY saved={saved}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
