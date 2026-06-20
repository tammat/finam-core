#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
from statistics import mean

import psycopg
from psycopg.rows import dict_row

LOOKBACK = 60
RANGE_WINDOW = 12

INDEX_SYMBOLS = ["IMOEX", "RTSI"]


def f(x):
    return float(x or 0.0)


def asset_class(symbol: str) -> str:
    if symbol in {"IMOEX", "RTSI"}:
        return "INDEX"
    if symbol.endswith("@MISX"):
        return "EQUITY"
    if symbol.startswith("BR"):
        return "BRENT_FUTURES"
    if symbol.startswith("NG"):
        return "GAS_FUTURES"
    if symbol.startswith(("GD", "GL")):
        return "GOLD_FUTURES"
    if symbol.startswith("SV"):
        return "SILVER_FUTURES"
    if "RUB" in symbol:
        return "FX"
    return "OTHER"


def calc_row(symbol: str, timeframe: str, bars: list[dict]) -> dict:
    if len(bars) < 20:
        return {
            "symbol": symbol,
            "asset_class": asset_class(symbol),
            "timeframe": timeframe,
            "bars": len(bars),
            "status": "NO_ENOUGH_BARS",
            "compression_score": 0.0,
            "expansion_score": 0.0,
        }

    rows = list(reversed(bars))
    closes = [f(r["close"]) for r in rows]
    highs = [f(r["high"]) for r in rows]
    lows = [f(r["low"]) for r in rows]
    vols = [f(r["volume"]) for r in rows]

    last_close = closes[-1]
    prev_close = closes[-2] if len(closes) > 1 else last_close

    ranges = [
        (highs[i] - lows[i]) / closes[i]
        for i in range(len(rows))
        if closes[i] > 0
    ]
    recent_ranges = ranges[-RANGE_WINDOW:]
    avg_range = mean(ranges[-LOOKBACK:]) if ranges else 0.0
    recent_range = mean(recent_ranges) if recent_ranges else 0.0

    atr_pct = avg_range
    range_pct = recent_range

    avg_volume = mean(vols[-LOOKBACK:-1]) if len(vols) > 10 else 0.0
    volume_ratio = vols[-1] / avg_volume if avg_volume > 0 else 0.0

    range_high = max(highs[-RANGE_WINDOW:])
    range_low = min(lows[-RANGE_WINDOW:])
    box_pct = (range_high - range_low) / last_close if last_close > 0 else 0.0

    trend_pct = (last_close - closes[-20]) / closes[-20] if closes[-20] > 0 else 0.0

    compression_score = 0.0
    if avg_range > 0:
        compression_score += max(0.0, min(1.0, 1.0 - recent_range / avg_range)) * 0.55
    compression_score += max(0.0, min(1.0, 0.01 / box_pct if box_pct > 0 else 0.0)) * 0.30
    compression_score += max(0.0, min(1.0, volume_ratio / 1.0)) * 0.15

    breakout_up = last_close >= range_high
    breakout_down = last_close <= range_low
    volume_expansion = volume_ratio >= 1.2
    range_expansion = recent_range > avg_range * 1.15 if avg_range > 0 else False

    expansion_score = 0.0
    expansion_score += 0.35 if breakout_up or breakout_down else 0.0
    expansion_score += 0.35 if volume_expansion else 0.0
    expansion_score += 0.20 if range_expansion else 0.0
    expansion_score += min(abs(trend_pct) / 0.01, 1.0) * 0.10

    if expansion_score >= 0.70 and compression_score >= 0.35:
        status = "EXPANSION_CANDIDATE"
    elif compression_score >= 0.55:
        status = "COMPRESSION"
    else:
        status = "NO_SETUP"

    return {
        "symbol": symbol,
        "asset_class": asset_class(symbol),
        "timeframe": timeframe,
        "bars": len(bars),
        "last_close": round(last_close, 6),
        "prev_close": round(prev_close, 6),
        "atr_pct": round(atr_pct, 8),
        "range_pct": round(range_pct, 8),
        "box_pct": round(box_pct, 8),
        "volume_ratio": round(volume_ratio, 6),
        "trend_pct": round(trend_pct, 8),
        "range_high": round(range_high, 6),
        "range_low": round(range_low, 6),
        "compression_score": round(compression_score, 6),
        "expansion_score": round(expansion_score, 6),
        "status": status,
    }


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL_NOT_SET")

    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                select symbol, coalesce(timeframe, 'M5') as timeframe
                from runtime_active_universe
                where is_enabled = true
                  and symbol like '%@MISX'
                order by priority desc nulls last, score desc nulls last, symbol
            """)
            equities = [dict(r) for r in cur.fetchall()]

            universe = []
            universe.extend(equities)
            universe.extend({"symbol": s, "timeframe": "M5"} for s in INDEX_SYMBOLS)

            cur.execute("""
                select symbol, timeframe
                from market_bars
                where timeframe in ('M1', 'M5')
                  and (
                    symbol like 'BR%@RTSX'
                    or symbol like 'NG%@RTSX'
                    or symbol like 'GD%@RTSX'
                    or symbol like 'GL%@RTSX'
                    or symbol like 'SV%@RTSX'
                    or symbol like '%RUB%@RTSX'
                  )
                group by symbol, timeframe
                having count(*) >= 60
                order by max(ts) desc
                limit 20
            """)
            futures = [dict(r) for r in cur.fetchall()]
            universe.extend(futures)

            seen = set()
            final_universe = []
            for row in universe:
                key = (row["symbol"], row["timeframe"])
                if key in seen:
                    continue
                seen.add(key)
                final_universe.append(row)

            results = []
            for item in final_universe:
                cur.execute("""
                    select ts, open, high, low, close, volume
                    from market_bars
                    where symbol = %s
                      and timeframe = %s
                    order by ts desc
                    limit %s
                """, (item["symbol"], item["timeframe"], LOOKBACK + 5))
                bars = list(cur.fetchall())
                results.append(calc_row(item["symbol"], item["timeframe"], bars))

    compression_count = sum(1 for r in results if r["status"] == "COMPRESSION")
    expansion_count = sum(1 for r in results if r["status"] == "EXPANSION_CANDIDATE")
    no_setup = sum(1 for r in results if r["status"] == "NO_SETUP")
    no_bars = sum(1 for r in results if r["status"] == "NO_ENOUGH_BARS")

    out = {
        "verdict": "MULTI_ASSET_COMPRESSION_EXPANSION_WATCH_READY",
        "mode": "read_only",
        "db_update": 0,
        "runtime_changed": 0,
        "execution_changed": 0,
        "telegram_send": 0,
        "rows_total": len(results),
        "equities_total": sum(1 for r in results if r["asset_class"] == "EQUITY"),
        "futures_total": sum(1 for r in results if "FUTURES" in r["asset_class"] or r["asset_class"] == "FX"),
        "indexes_total": sum(1 for r in results if r["asset_class"] == "INDEX"),
        "compression_count": compression_count,
        "expansion_candidate_count": expansion_count,
        "no_setup": no_setup,
        "no_bars": no_bars,
        "rows": sorted(results, key=lambda r: (r["status"] == "EXPANSION_CANDIDATE", r["compression_score"], r["expansion_score"]), reverse=True),
    }

    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))

    for r in out["rows"]:
        print(
            "MULTI_ASSET_COMPRESSION_ROW "
            f"symbol={r['symbol']} "
            f"asset_class={r['asset_class']} "
            f"timeframe={r['timeframe']} "
            f"status={r['status']} "
            f"compression_score={r.get('compression_score', 0)} "
            f"expansion_score={r.get('expansion_score', 0)}",
            flush=True,
        )

    print("VERDICT=MULTI_ASSET_COMPRESSION_EXPANSION_WATCH_READY")
    print("TEST_MULTI_ASSET_COMPRESSION_EXPANSION_WATCH_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
