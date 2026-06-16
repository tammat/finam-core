#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

SQL = """
insert into rebuild_candidates_v1 (
    symbol,
    strategy,
    timeframe,
    trade_source,
    quarantine_status,
    quarantine_reason,
    rebuild_status,
    rebuild_action,
    rebuild_reason,
    runtime_allowed,
    execution_enabled
)
values (
    'GDU6@RTSX',
    'gold_short_only_shadow_v1',
    'M5',
    'paper',
    'ACTIVE',
    'gold_clean_v3_rebuild_candidate',
    'PLANNED',
    'REBUILD_V3',
    'gold_short_only_clean_paper_v3_rebuild',
    false,
    false
)
on conflict do nothing;
"""

REPORT = """
select
    symbol,
    strategy,
    timeframe,
    trade_source,
    quarantine_status,
    quarantine_reason,
    rebuild_status,
    rebuild_action,
    rebuild_reason,
    runtime_allowed,
    execution_enabled
from rebuild_candidates_v1
where symbol='GDU6@RTSX'
  and strategy='gold_short_only_shadow_v1'
  and timeframe='M5'
  and trade_source='paper';
"""

def main() -> int:
    print("=== GOLD V3 REBUILD CANDIDATE REGISTER V1 ===")
    print("mode=research_only")
    print("runtime_allow=0")
    print("execution_enabled=0")

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL)
            cur.execute(REPORT)
            rows = cur.fetchall()
        conn.commit()

    if not rows:
        raise SystemExit("FAIL: gold rebuild candidate was not registered")

    for r in rows:
        print(
            "GOLD_V3_REBUILD_CANDIDATE_ROW "
            f"symbol={r['symbol']} "
            f"strategy={r['strategy']} "
            f"timeframe={r['timeframe']} "
            f"trade_source={r['trade_source']} "
            f"quarantine_status={r['quarantine_status']} "
            f"rebuild_status={r['rebuild_status']} "
            f"rebuild_action={r['rebuild_action']} "
            f"runtime_allow={int(bool(r['runtime_allowed']))} "
            f"execution_enabled={int(bool(r['execution_enabled']))}"
        )

    print("GOLD_V3_REBUILD_CANDIDATE_REGISTER_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
