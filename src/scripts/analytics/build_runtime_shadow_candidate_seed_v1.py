#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

ROWS = [
    {
        "symbol": "USDRUBF@RTSX",
        "root": "USD",
        "strategy": "usd_shadow_watch_v1",
        "timeframe": "M5",
        "side": "WATCH",
        "reason": "seed_shadow_candidate_usd",
    },
    {
        "symbol": "LKOH@MISX",
        "root": "LKOH",
        "strategy": "lkoh_shadow_watch_v1",
        "timeframe": "M5",
        "side": "WATCH",
        "reason": "seed_shadow_candidate_lkoh",
    },
]

SQL = """
INSERT INTO runtime_shadow_candidate_signals_v1 (
    symbol, root, strategy, timeframe,
    signal_ts, side, entry_price, qty,
    shadow_only, runtime_allow, execution_enabled,
    reason, source, raw_json
)
VALUES (
    %(symbol)s, %(root)s, %(strategy)s, %(timeframe)s,
    now(), %(side)s, NULL, NULL,
    1, 0, 0,
    %(reason)s, 'runtime_shadow_candidate_seed_v1',
    jsonb_build_object(
        'seed', true,
        'runtime_changed', 0,
        'execution_enabled', 0
    )
)
ON CONFLICT (symbol, strategy, timeframe, signal_ts, side)
DO NOTHING;
"""

def main() -> None:
    dsn = os.environ["DATABASE_URL"]

    print("=== RUNTIME SHADOW CANDIDATE SEED V1 ===")
    print("mode=seed_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print("table=runtime_shadow_candidate_signals_v1")
    print()

    inserted = 0

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            for row in ROWS:
                cur.execute(SQL, row)
                inserted += cur.rowcount

            cur.execute("""
                SELECT
                    symbol,
                    strategy,
                    timeframe,
                    side,
                    shadow_only,
                    runtime_allow,
                    execution_enabled,
                    reason,
                    source,
                    created_at
                FROM runtime_shadow_candidate_signals_v1
                WHERE source='runtime_shadow_candidate_seed_v1'
                ORDER BY created_at DESC, id DESC
                LIMIT 10;
            """)
            rows = cur.fetchall()

    print("SEED_ROWS")
    for r in rows:
        print(
            "SEED_ROW "
            f"symbol={r['symbol']} "
            f"strategy={r['strategy']} "
            f"timeframe={r['timeframe']} "
            f"side={r['side']} "
            f"shadow_only={r['shadow_only']} "
            f"runtime_allow={r['runtime_allow']} "
            f"execution_enabled={r['execution_enabled']} "
            f"reason={r['reason']} "
            f"source={r['source']} "
            f"created_at={r['created_at']}"
        )

    print()
    print(f"SUMMARY_ROW inserted={inserted} source=runtime_shadow_candidate_seed_v1")
    print("VERDICT=RUNTIME_SHADOW_CANDIDATE_SEED_RECORDED")
    print("RUNTIME_SHADOW_CANDIDATE_SEED_V1_OK")

if __name__ == "__main__":
    main()
