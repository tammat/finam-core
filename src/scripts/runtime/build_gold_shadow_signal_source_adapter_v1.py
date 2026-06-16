#!/usr/bin/env python3
from __future__ import annotations

import json
import os

import psycopg2
import psycopg2.extras

SYMBOL = "GDU6@RTSX"
STRATEGY = "gold_short_only_shadow_v1"

DDL = """
CREATE TABLE IF NOT EXISTS gold_shadow_signals (
    id BIGSERIAL PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now(),
    symbol text NOT NULL,
    strategy text NOT NULL,
    timeframe text NOT NULL DEFAULT 'M5',
    signal_ts timestamptz NOT NULL,
    side text NOT NULL,
    entry_price numeric,
    reason text,
    shadow_only boolean NOT NULL DEFAULT true,
    runtime_allowed boolean NOT NULL DEFAULT false,
    execution_enabled boolean NOT NULL DEFAULT false,
    raw_json jsonb,
    UNIQUE(symbol, strategy, timeframe, signal_ts, side)
);

CREATE INDEX IF NOT EXISTS idx_gold_shadow_signals_symbol_ts
ON gold_shadow_signals(symbol, signal_ts DESC);
"""

SQL_SOURCE = """
SELECT
    symbol,
    COALESCE(strategy, 'gold_short_only_shadow_v1') AS strategy,
    timeframe,
    signal_ts,
    side,
    entry_price,
    COALESCE(reason, 'runtime_shadow_gold_signals_adapter_v1') AS reason
FROM runtime_shadow_gold_signals
WHERE symbol=%s
ORDER BY signal_ts;
"""

SQL_FALLBACK = """
SELECT
    symbol,
    COALESCE(strategy, 'gold_short_only_shadow_v1') AS strategy,
    timeframe,
    signal_ts,
    side,
    entry_price,
    COALESCE(reason, 'runtime_shadow_gold_signals_adapter_v1') AS reason
FROM runtime_shadow_gold_signals
WHERE symbol=%s
ORDER BY signal_ts;
"""

INSERT = """
INSERT INTO gold_shadow_signals (
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

def table_exists(cur, table_name: str) -> bool:
    cur.execute(
        """
        SELECT EXISTS (
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema='public'
              AND table_name=%s
        );
        """,
        (table_name,),
    )
    return bool(cur.fetchone()["exists"])

def main() -> int:
    print("=== GOLD SHADOW SIGNAL SOURCE ADAPTER V1 ===")
    print("mode=source_adapter")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"symbol={SYMBOL}")
    print(f"strategy={STRATEGY}")
    print()

    inserted = 0
    total = 0
    source_table = None

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(DDL)

            if table_exists(cur, "runtime_shadow_gold_signals"):
                source_table = "runtime_shadow_gold_signals"
                cur.execute(SQL_SOURCE, (SYMBOL,))
            elif table_exists(cur, "gold_shadow_filtered_trades"):
                source_table = "gold_shadow_filtered_trades"
                cur.execute(SQL_FALLBACK, (SYMBOL,))
            else:
                print("ADAPTER_ERROR reason=no_gold_shadow_source_table")
                print("runtime_allow=0")
                print("execution_enabled=0")
                return 1

            rows = cur.fetchall()

            for row in rows:
                total += 1
                payload = dict(row)
                payload["source_table"] = source_table
                payload["shadow_only"] = True
                payload["runtime_allowed"] = False
                payload["execution_enabled"] = False

                cur.execute(
                    INSERT,
                    {
                        "symbol": row["symbol"],
                        "strategy": row.get("strategy") or STRATEGY,
                        "signal_ts": row["signal_ts"],
                        "side": row["side"],
                        "entry_price": row["entry_price"],
                        "reason": row["reason"],
                        "raw_json": json.dumps(payload, ensure_ascii=False, default=str),
                    },
                )
                inserted += 1 if cur.rowcount == 1 else 0

        conn.commit()

    print(
        "ADAPTER_ROW "
        f"symbol={SYMBOL} "
        f"source_table={source_table} "
        f"signals_found={total} "
        f"inserted={inserted} "
        "runtime_allowed=0 "
        "execution_enabled=0"
    )
    print()
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("VERDICT=GOLD_SHADOW_SIGNAL_SOURCE_READY")
    print("GOLD_SHADOW_SIGNAL_SOURCE_ADAPTER_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
