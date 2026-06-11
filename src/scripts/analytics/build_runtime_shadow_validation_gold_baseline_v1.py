#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

MIN_SIGNALS = 50

SQL = """
SELECT
    symbol,
    timeframe,
    strategy,
    COUNT(*) AS shadow_signals,
    COUNT(DISTINCT signal_ts) AS distinct_signal_ts,
    MIN(signal_ts) AS first_shadow_ts,
    MAX(signal_ts) AS last_shadow_ts,
    ROUND(
        EXTRACT(EPOCH FROM (MAX(signal_ts)-MIN(signal_ts))) / 86400.0,
        4
    ) AS days_observed,
    COUNT(*) FILTER (WHERE shadow_only IS TRUE) AS shadow_only_rows,
    COUNT(*) FILTER (WHERE shadow_only IS DISTINCT FROM TRUE) AS unsafe_rows
FROM runtime_shadow_gold_signals
WHERE symbol='GDU6@RTSX'
  AND strategy='gold_short_only_shadow_v1'
GROUP BY symbol, timeframe, strategy
ORDER BY symbol, timeframe, strategy;
"""

def main() -> None:
    dsn = os.environ["DATABASE_URL"]

    print("=== RUNTIME SHADOW VALIDATION GOLD BASELINE V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print("symbol=GDU6@RTSX")
    print("strategy=gold_short_only_shadow_v1")
    print(f"min_signals={MIN_SIGNALS}")
    print()

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL)
            rows = cur.fetchall()

    if not rows:
        print("BASELINE_ROW status=NO_DATA shadow_signals=0 remaining_signals=50")
        print("VERDICT=GOLD_BASELINE_NO_DATA")
        print("RUNTIME_SHADOW_VALIDATION_GOLD_BASELINE_V1_OK")
        return

    print("BASELINE_ROWS")
    for r in rows:
        signals = int(r["shadow_signals"] or 0)
        remaining = max(0, MIN_SIGNALS - signals)
        unsafe = int(r["unsafe_rows"] or 0)

        if unsafe > 0:
            status = "UNSAFE"
        elif signals >= MIN_SIGNALS:
            status = "READY_FOR_SCORECARD"
        else:
            status = "ACCUMULATING"

        print(
            "BASELINE_ROW "
            f"symbol={r['symbol']} "
            f"timeframe={r['timeframe']} "
            f"strategy={r['strategy']} "
            f"shadow_signals={signals} "
            f"distinct_signal_ts={r['distinct_signal_ts']} "
            f"first_shadow_ts={r['first_shadow_ts']} "
            f"last_shadow_ts={r['last_shadow_ts']} "
            f"days_observed={r['days_observed']} "
            f"shadow_only_rows={r['shadow_only_rows']} "
            f"unsafe_rows={unsafe} "
            f"remaining_signals={remaining} "
            f"status={status}"
        )

    print()
    print("VERDICT=GOLD_BASELINE_RECORDED")
    print("RUNTIME_SHADOW_VALIDATION_GOLD_BASELINE_V1_OK")

if __name__ == "__main__":
    main()
