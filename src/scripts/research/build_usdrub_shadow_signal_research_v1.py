#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from decimal import Decimal

import psycopg2
import psycopg2.extras

SYMBOL = "USDRUBF@RTSX"
STRATEGY = "usdrub_shadow_signal_research_v1"

DDL = """
CREATE TABLE IF NOT EXISTS usdrub_shadow_signals (
    id BIGSERIAL PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now(),
    symbol text NOT NULL,
    strategy text NOT NULL,
    timeframe text NOT NULL,
    signal_ts timestamptz NOT NULL,
    side text NOT NULL,
    entry_price numeric NOT NULL,
    reason text,
    shadow_only boolean NOT NULL DEFAULT true,
    runtime_allowed boolean NOT NULL DEFAULT false,
    execution_enabled boolean NOT NULL DEFAULT false,
    raw_json jsonb,
    UNIQUE(symbol, strategy, timeframe, signal_ts, side)
);

CREATE INDEX IF NOT EXISTS idx_usdrub_shadow_signals_symbol_ts
ON usdrub_shadow_signals(symbol, signal_ts DESC);
"""

SQL = """
WITH bars AS (
    SELECT
        ts,
        open::numeric AS open,
        high::numeric AS high,
        low::numeric AS low,
        close::numeric AS close,
        LAG(close::numeric, 1) OVER (ORDER BY ts) AS prev_close,
        AVG(close::numeric) OVER (
            ORDER BY ts ROWS BETWEEN 12 PRECEDING AND 1 PRECEDING
        ) AS ma12,
        AVG(close::numeric) OVER (
            ORDER BY ts ROWS BETWEEN 36 PRECEDING AND 1 PRECEDING
        ) AS ma36
    FROM market_bars
    WHERE symbol=%s
      AND timeframe='M5'
),
signals AS (
    SELECT
        ts AS signal_ts,
        close AS entry_price,
        CASE
            WHEN prev_close IS NOT NULL
             AND ma12 IS NOT NULL
             AND ma36 IS NOT NULL
             AND close > ma12
             AND ma12 > ma36
             AND close > prev_close
            THEN 'BUY'
            WHEN prev_close IS NOT NULL
             AND ma12 IS NOT NULL
             AND ma36 IS NOT NULL
             AND close < ma12
             AND ma12 < ma36
             AND close < prev_close
            THEN 'SELL'
            ELSE NULL
        END AS side,
        CASE
            WHEN prev_close IS NOT NULL
             AND ma12 IS NOT NULL
             AND ma36 IS NOT NULL
             AND close > ma12
             AND ma12 > ma36
             AND close > prev_close
            THEN 'usdrub_m5_uptrend_momentum'
            WHEN prev_close IS NOT NULL
             AND ma12 IS NOT NULL
             AND ma36 IS NOT NULL
             AND close < ma12
             AND ma12 < ma36
             AND close < prev_close
            THEN 'usdrub_m5_downtrend_momentum'
            ELSE NULL
        END AS reason,
        ma12,
        ma36,
        prev_close
    FROM bars
)
SELECT *
FROM signals
WHERE side IS NOT NULL
ORDER BY signal_ts;
"""

INSERT = """
INSERT INTO usdrub_shadow_signals (
    symbol,
    strategy,
    timeframe,
    signal_ts,
    side,
    entry_price,
    reason,
    shadow_only,
    runtime_allowed,
    execution_enabled,
    raw_json
)
VALUES (
    %(symbol)s,
    %(strategy)s,
    'M5',
    %(signal_ts)s,
    %(side)s,
    %(entry_price)s,
    %(reason)s,
    true,
    false,
    false,
    %(raw_json)s
)
ON CONFLICT(symbol, strategy, timeframe, signal_ts, side) DO NOTHING;
"""

def jsonable(v):
    if isinstance(v, Decimal):
        return float(v)
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return v

def main() -> int:
    print("=== USDRUB SHADOW SIGNAL RESEARCH V1 ===")
    print("mode=shadow_research")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"symbol={SYMBOL}")
    print(f"strategy={STRATEGY}")
    print()

    inserted = 0
    total = 0
    buy = 0
    sell = 0

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(DDL)
            cur.execute(SQL, (SYMBOL,))
            rows = cur.fetchall()

            print("USDRUB_SIGNAL_ROWS")

            for row in rows:
                total += 1
                if row["side"] == "BUY":
                    buy += 1
                elif row["side"] == "SELL":
                    sell += 1

                payload = {k: jsonable(v) for k, v in dict(row).items()}
                payload["symbol"] = SYMBOL
                payload["strategy"] = STRATEGY
                payload["shadow_only"] = True
                payload["runtime_allowed"] = False
                payload["execution_enabled"] = False

                cur.execute(
                    INSERT,
                    {
                        "symbol": SYMBOL,
                        "strategy": STRATEGY,
                        "signal_ts": row["signal_ts"],
                        "side": row["side"],
                        "entry_price": row["entry_price"],
                        "reason": row["reason"],
                        "raw_json": json.dumps(payload, ensure_ascii=False),
                    },
                )
                if cur.rowcount == 1:
                    inserted += 1

            conn.commit()

    print(
        "USDRUB_SIGNAL_SUMMARY "
        f"signals_found={total} "
        f"inserted={inserted} "
        f"buy={buy} "
        f"sell={sell}"
    )
    print()
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("VERDICT=USDRUB_SHADOW_SIGNALS_RECORDED")
    print("USDRUB_SHADOW_SIGNAL_RESEARCH_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
