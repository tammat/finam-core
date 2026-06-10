#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

SYMBOLS = ["USDRUBF@RTSX", "LKOH@MISX"]

SQL_INSERT = """
INSERT INTO runtime_shadow_candidate_signals_v1 (
    symbol, root, strategy, timeframe,
    signal_ts, side, entry_price, qty,
    shadow_only, runtime_allow, execution_enabled,
    reason, source, raw_json
)
SELECT
    s.symbol,
    CASE
        WHEN s.symbol='USDRUBF@RTSX' THEN 'USD'
        WHEN s.symbol='LKOH@MISX' THEN 'LKOH'
        ELSE s.symbol
    END AS root,
    CASE
        WHEN s.symbol='USDRUBF@RTSX' THEN 'usd_shadow_watch_v1'
        WHEN s.symbol='LKOH@MISX' THEN 'lkoh_shadow_watch_v1'
        ELSE 'shadow_watch_v1'
    END AS strategy,
    COALESCE(s.timeframe, 'M5') AS timeframe,
    COALESCE(s.ts, s.created_at) AS signal_ts,
    COALESCE(s.side, 'WATCH') AS side,
    s.entry_price,
    s.qty,
    1 AS shadow_only,
    0 AS runtime_allow,
    0 AS execution_enabled,
    'collected_from_signals' AS reason,
    'runtime_shadow_candidate_collector_v1' AS source,
    jsonb_build_object(
        'signal_row_id', s.id,
        'signal_id', s.signal_id,
        'original_strategy', s.strategy,
        'status', s.status,
        'runtime_changed', 0,
        'execution_enabled', 0,
        'collector', 'runtime_shadow_candidate_collector_v1'
    ) AS raw_json
FROM signals s
WHERE s.symbol = ANY(%s)
  AND COALESCE(s.ts, s.created_at) IS NOT NULL
ON CONFLICT (symbol, strategy, timeframe, signal_ts, side)
DO NOTHING;
"""

SQL_SUMMARY = """
SELECT
    symbol,
    strategy,
    COUNT(*) AS rows,
    COUNT(*) FILTER (WHERE runtime_allow=1) AS runtime_allow_rows,
    COUNT(*) FILTER (WHERE execution_enabled=1) AS execution_enabled_rows,
    MAX(signal_ts) AS last_signal_ts
FROM runtime_shadow_candidate_signals_v1
WHERE source='runtime_shadow_candidate_collector_v1'
GROUP BY symbol, strategy
ORDER BY symbol, strategy;
"""

def main() -> None:
    dsn = os.environ["DATABASE_URL"]

    print("=== RUNTIME SHADOW CANDIDATE COLLECTOR V1 ===")
    print("mode=collector_shadow_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print("symbols=USDRUBF@RTSX,LKOH@MISX")
    print()

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL_INSERT, (SYMBOLS,))
            inserted = cur.rowcount

            cur.execute(SQL_SUMMARY)
            rows = cur.fetchall()

    print("COLLECTOR_ROWS")
    for r in rows:
        print(
            "COLLECTOR_ROW "
            f"symbol={r['symbol']} "
            f"strategy={r['strategy']} "
            f"rows={r['rows']} "
            f"runtime_allow_rows={r['runtime_allow_rows']} "
            f"execution_enabled_rows={r['execution_enabled_rows']} "
            f"last_signal_ts={r['last_signal_ts']}"
        )

    print()
    print(f"SUMMARY_ROW inserted={inserted} source=runtime_shadow_candidate_collector_v1")
    print("VERDICT=RUNTIME_SHADOW_CANDIDATE_COLLECTOR_RECORDED")
    print("RUNTIME_SHADOW_CANDIDATE_COLLECTOR_V1_OK")

if __name__ == "__main__":
    main()
