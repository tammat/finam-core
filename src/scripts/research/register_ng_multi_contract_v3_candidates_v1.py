#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

CANDIDATES = [
    ("NGM6@RTSX", "NG_CONSERVATIVE_BREAKOUT", "M5", "paper"),
    ("NGQ6@RTSX", "NG_CONSERVATIVE_BREAKOUT", "M5", "paper"),
    ("NGM6@RTSX", "NG_CONSERVATIVE_BREAKOUT_M1", "M1", "paper"),
    ("NGQ6@RTSX", "NG_CONSERVATIVE_BREAKOUT_M1", "M1", "paper"),
]

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
    %(symbol)s,
    %(strategy)s,
    %(timeframe)s,
    %(trade_source)s,
    'ACTIVE',
    'ng_multi_contract_v3_candidate',
    'PLANNED',
    'REBUILD_V3',
    'ng_multi_contract_clean_v3_rebuild',
    false,
    false
)

on conflict (symbol, strategy, timeframe, trade_source)
do update set
    quarantine_status='ACTIVE',
    quarantine_reason='ng_multi_contract_v3_candidate',
    rebuild_status='PLANNED',
    rebuild_action='REBUILD_V3',
    rebuild_reason='ng_multi_contract_clean_v3_rebuild',
    runtime_allowed=false,
    execution_enabled=false;

"""

REPORT = """
select
    symbol,
    strategy,
    timeframe,
    trade_source,
    quarantine_status,
    rebuild_status,
    rebuild_action,
    runtime_allowed,
    execution_enabled
from rebuild_candidates_v1
where symbol in ('NGM6@RTSX','NGQ6@RTSX')
  and strategy in ('NG_CONSERVATIVE_BREAKOUT','NG_CONSERVATIVE_BREAKOUT_M1')
  and trade_source='paper'
order by symbol, strategy, timeframe;
"""

def main() -> int:
    print("=== NG MULTI CONTRACT V3 CANDIDATES V1 ===")
    print("mode=research_only")
    print("runtime_allow=0")
    print("execution_enabled=0")

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            for symbol, strategy, timeframe, trade_source in CANDIDATES:
                cur.execute(SQL, {
                    "symbol": symbol,
                    "strategy": strategy,
                    "timeframe": timeframe,
                    "trade_source": trade_source,
                })

            cur.execute(REPORT)
            rows = cur.fetchall()

        conn.commit()

    for r in rows:
        print(
            "NG_MULTI_CONTRACT_V3_CANDIDATE_ROW "
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

    if len(rows) < 4:
        raise SystemExit(f"FAIL: expected 4 NG candidates, got {len(rows)}")

    print("NG_MULTI_CONTRACT_V3_CANDIDATES_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
