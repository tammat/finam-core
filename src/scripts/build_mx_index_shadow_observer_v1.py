from __future__ import annotations

import os
from decimal import Decimal

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SYMBOL = "MXU6@RTSX"
SOURCE_VERSION = "MX_INDEX_SHADOW_OBSERVER_V1"


def breakout(prior: list[dict], current: dict) -> tuple[str, Decimal, Decimal] | None:
    if len(prior) < 20:
        return None
    recent = prior[-20:]
    high = max(Decimal(str(row["high"])) for row in recent)
    low = min(Decimal(str(row["low"])) for row in recent)
    true_ranges = [Decimal(str(row["high"])) - Decimal(str(row["low"])) for row in prior[-14:]]
    atr = sum(true_ranges, Decimal("0")) / Decimal(len(true_ranges))
    close = Decimal(str(current["close"]))
    if atr <= 0:
        return None
    if close > high:
        return "LONG", close - Decimal("1.8") * atr, close + Decimal("3.2") * atr
    if close < low:
        return "SHORT", close + Decimal("1.8") * atr, close - Decimal("3.2") * atr
    return None


def main() -> int:
    with psycopg2.connect(DB) as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("""SELECT ts,open,high,low,close FROM market_bars
                WHERE symbol=%s AND timeframe='M5'
                  AND ts < date_trunc('minute',clock_timestamp())-interval '5 minutes'
                ORDER BY ts DESC LIMIT 61""", (SYMBOL,))
            bars = list(reversed(cursor.fetchall()))
            if len(bars) < 21:
                print(f"bars={len(bars)} VERDICT=MX_INDEX_SHADOW_WAITING_BARS")
                return 0
            current, prior = bars[-1], bars[:-1]
            decision = breakout(prior, current)
            if decision is None:
                print(f"bar_ts={current['ts']} signal=NONE VERDICT=MX_INDEX_SHADOW_NO_SIGNAL")
                return 0
            side, stop, take = decision
            cursor.execute("""SELECT regime_code FROM analytics.rvi_regime_state_v1
                ORDER BY bar_ts DESC LIMIT 1""")
            rvi = cursor.fetchone()
            cursor.execute("""INSERT INTO analytics.mx_index_shadow_signal_v1(
                symbol,signal_ts,side,entry_price,stop_price,take_price,entry_reason,
                rvi_regime,shadow_only,paper_allowed,live_allowed,source_version)
              VALUES(%s,%s,%s,%s,%s,%s,'20-bar confirmed close breakout',%s,true,false,false,%s)
              ON CONFLICT(symbol,timeframe,signal_ts,side) DO NOTHING""",
              (SYMBOL,current["ts"],side,current["close"],stop,take,
               (rvi or {}).get("regime_code","UNKNOWN"),SOURCE_VERSION))
            inserted = cursor.rowcount
    print(f"bar_ts={current['ts']} side={side} entry={current['close']} stop={stop} take={take} inserted={inserted}")
    print("shadow_only=1 paper_allowed=0 live_allowed=0")
    print("VERDICT=MX_INDEX_SHADOW_OBSERVER_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
