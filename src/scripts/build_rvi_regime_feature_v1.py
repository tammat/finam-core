from __future__ import annotations

import os
from decimal import Decimal

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SYMBOL = "VIU6@RTSX"
SOURCE_VERSION = "RVI_REGIME_FEATURE_V1"


def regime(percentile: Decimal) -> str:
    if percentile >= Decimal("0.75"):
        return "HIGH_VOL"
    if percentile <= Decimal("0.25"):
        return "LOW_VOL"
    return "NORMAL_VOL"


def main() -> int:
    with psycopg2.connect(DB) as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("""
                SELECT ts,close,
                  percent_rank() OVER(ORDER BY close) percentile
                FROM (SELECT ts,close FROM market_bars
                      WHERE symbol=%s AND timeframe='M1'
                        AND ts < date_trunc('minute',clock_timestamp())
                      ORDER BY ts DESC LIMIT 240) bars ORDER BY ts DESC LIMIT 1
            """, (SYMBOL,))
            row = cursor.fetchone()
            if not row:
                print("VERDICT=RVI_REGIME_WAITING_BARS")
                return 0
            percentile = Decimal(str(row["percentile"] or 0))
            cursor.execute("""
                INSERT INTO analytics.rvi_regime_state_v1(
                  symbol,bar_ts,rvi_value,rolling_percentile,regime_code,source_version)
                VALUES(%s,%s,%s,%s,%s,%s)
                ON CONFLICT(symbol,bar_ts) DO UPDATE SET
                  rvi_value=excluded.rvi_value,rolling_percentile=excluded.rolling_percentile,
                  regime_code=excluded.regime_code,source_version=excluded.source_version,
                  calculated_at=clock_timestamp()
            """, (SYMBOL,row["ts"],row["close"],percentile,regime(percentile),SOURCE_VERSION))
    print(f"symbol={SYMBOL} bar_ts={row['ts']} rvi={row['close']} percentile={percentile} regime={regime(percentile)}")
    print("trading_allowed=0 paper_allowed=0 live_allowed=0")
    print("VERDICT=RVI_REGIME_FEATURE_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
