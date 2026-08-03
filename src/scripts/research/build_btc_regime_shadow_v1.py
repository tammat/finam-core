from __future__ import annotations

import math
import os
from datetime import datetime, timezone

import psycopg
from psycopg.rows import dict_row


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "BTC_REGIME_SHADOW_V1"


def pct(current: float, previous: float) -> float | None:
    return current / previous - 1.0 if previous > 0 else None


def classify(return_1h: float | None, return_24h: float | None,
             realized_vol_1h: float | None) -> str:
    one_hour = return_1h or 0.0
    one_day = return_24h or 0.0
    volatility = realized_vol_1h or 0.0
    if abs(one_hour) >= 0.02 or volatility >= 0.012:
        return "SHOCK"
    if one_hour <= -0.005 and one_day < 0:
        return "RISK_OFF"
    if one_hour >= 0.005 and one_day > 0:
        return "RISK_ON"
    return "NEUTRAL"


def main() -> int:
    with psycopg.connect(DB, row_factory=dict_row) as connection:
        rows = connection.execute(
            """
            SELECT ts,close FROM market_bars
            WHERE symbol='BTCUSD' AND timeframe='M5' AND close>0
            ORDER BY ts DESC LIMIT 289
            """
        ).fetchall()
        if len(rows) < 13:
            print(f"BTC_REGIME_SHADOW_DEFERRED reason=INSUFFICIENT_BARS bars={len(rows)}")
            return 0

        rows = list(reversed(rows))
        closes = [float(row["close"]) for row in rows]
        current = closes[-1]

        def lag_return(bars: int) -> float | None:
            return pct(current, closes[-1-bars]) if len(closes) > bars else None

        log_returns = [math.log(closes[index] / closes[index - 1])
                       for index in range(max(1, len(closes) - 12), len(closes))]
        mean = sum(log_returns) / len(log_returns)
        realized_vol = math.sqrt(
            sum((value - mean) ** 2 for value in log_returns) / max(1, len(log_returns) - 1)
        )
        return_15m = lag_return(3)
        return_1h = lag_return(12)
        return_24h = lag_return(288)
        regime = classify(return_1h, return_24h, realized_vol)
        observed_at = datetime.now(timezone.utc)
        source_bar_ts = rows[-1]["ts"]

        connection.execute(
            """
            INSERT INTO analytics.btc_regime_shadow_v1(
                observed_at,source_bar_ts,return_15m,return_1h,return_24h,
                realized_vol_1h,regime_code,weekend_context,shadow_only,source_version
            ) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,true,%s)
            ON CONFLICT(observed_at) DO NOTHING
            """,
            (observed_at, source_bar_ts, return_15m, return_1h, return_24h,
             realized_vol, regime, source_bar_ts.weekday() >= 5, SOURCE_VERSION),
        )
        connection.commit()

    print(
        f"BTC_REGIME_SHADOW_WRITTEN source_bar_ts={source_bar_ts.isoformat()} "
        f"regime={regime} return_1h={return_1h} return_24h={return_24h} "
        "shadow_only=1 paper_changed=0 v5_changed=0 execution_changed=0"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
