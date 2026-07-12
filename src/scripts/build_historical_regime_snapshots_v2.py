from __future__ import annotations

import argparse
import math
import os
import statistics
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "HISTORICAL_REGIME_BUILDER_V2"
MOSCOW = ZoneInfo("Europe/Moscow")


def source_sql(symbol: str, timeframe: str) -> tuple[str, tuple]:
    if symbol == "BR_ROLLING@RTSX":
        return "SELECT ts,close FROM public.market_bars_br_m5_rolling_v2 ORDER BY ts", ()
    if symbol == "NG_ROLLING@RTSX":
        return "SELECT ts,close FROM public.market_bars_ng_m5_rolling_v1 ORDER BY ts", ()
    return (
        "SELECT ts,close FROM public.market_bars "
        "WHERE symbol=%s AND timeframe=%s AND close>0 ORDER BY ts",
        (symbol, timeframe),
    )


def session(ts: datetime) -> str:
    local = ts.astimezone(MOSCOW)
    minute = local.hour * 60 + local.minute
    if 600 <= minute < 630:
        return "MOEX_OPEN"
    if 630 <= minute < 660:
        return "MOEX_FIRST_HOUR"
    if 660 <= minute < 990:
        return "EUROPE_OVERLAP"
    if 990 <= minute < 1080:
        return "US_OPEN"
    if 1080 <= minute < 1420:
        return "EVENING"
    if 1420 <= minute < 1430:
        return "MOEX_CLOSE"
    return "OUTSIDE_SESSION"


def classify(closes: list[float], index: int) -> tuple[str, str, str, str, float, dict[str, Any]]:
    returns = [closes[i] / closes[i - 1] - 1.0 for i in range(max(1, index - 99), index + 1)]
    short = returns[-20:]
    long = returns
    vol20 = statistics.pstdev(short) if len(short) >= 20 else 0.0
    vol100 = statistics.pstdev(long) if len(long) >= 60 else vol20
    trend_return = closes[index] / closes[index - 20] - 1.0
    trend_threshold = max(0.002, vol20 * math.sqrt(20) * 0.75)
    if trend_return > trend_threshold:
        trend = "trend_up"
    elif trend_return < -trend_threshold:
        trend = "trend_down"
    else:
        trend = "range"
    ratio = vol20 / vol100 if vol100 > 0 else 1.0
    if ratio >= 1.25:
        volatility, compression = "expansion", "EXPANDED"
    elif ratio <= 0.75:
        volatility, compression = "compression", "COMPRESSED"
    else:
        volatility, compression = "normal", "NORMAL"
    if trend == "range":
        regime = "compression" if volatility == "compression" else f"range_{volatility}"
    else:
        regime = f"{trend}_expansion" if volatility == "expansion" else trend
    trend_strength = abs(trend_return) / trend_threshold if trend_threshold > 0 else 0.0
    confidence = min(0.99, 0.65 + min(0.24, abs(ratio - 1.0) * 0.20) + min(0.10, trend_strength * 0.04))
    return regime, volatility, trend, compression, confidence, {
        "return_20": trend_return, "volatility_20": vol20, "volatility_100": vol100,
        "volatility_ratio": ratio, "lookback_only": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", required=True)
    parser.add_argument("--timeframe", default="M5")
    args = parser.parse_args()
    symbols = [value.strip() for value in args.symbols.split(",") if value.strip()]
    total = 0
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            for symbol in symbols:
                query, params = source_sql(symbol, args.timeframe)
                cur.execute(query, params)
                bars = cur.fetchall()
                closes = [float(row["close"]) for row in bars]
                rows = []
                for index in range(100, len(bars)):
                    regime, volatility, trend, compression, confidence, payload = classify(closes, index)
                    ts = bars[index]["ts"]
                    rows.append((ts, ts.astimezone(MOSCOW).date(), symbol, args.timeframe, regime, volatility, trend,
                                 compression, "UNKNOWN", session(ts), confidence, SOURCE_VERSION, psycopg2.extras.Json(payload)))
                psycopg2.extras.execute_values(cur, """
                    INSERT INTO analytics_regime_snapshots_v2
                    (ts,trade_date,symbol,timeframe,regime,volatility_regime,trend_regime,compression_state,
                     intermarket_state,session_type,confidence,source,payload) VALUES %s
                    ON CONFLICT(ts,symbol,timeframe,source) DO UPDATE SET
                    regime=excluded.regime,volatility_regime=excluded.volatility_regime,trend_regime=excluded.trend_regime,
                    compression_state=excluded.compression_state,session_type=excluded.session_type,
                    confidence=excluded.confidence,payload=excluded.payload,updated_at=now()
                """, rows, page_size=2000)
                total += len(rows)
                print(f"symbol={symbol} bars={len(bars)} snapshots={len(rows)}")
    print(f"snapshots_total={total}")
    print("lookahead_allowed=0")
    print("VERDICT=HISTORICAL_REGIME_BUILDER_V2_OK")


if __name__ == "__main__":
    main()
