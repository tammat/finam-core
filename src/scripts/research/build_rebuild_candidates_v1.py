#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

DDL = """
create table if not exists rebuild_candidates_v1 (
    id bigserial primary key,
    created_at timestamptz not null default now(),

    symbol text not null,
    strategy text not null,
    timeframe text not null,
    trade_source text not null,

    quarantine_status text not null,
    quarantine_reason text not null,

    rebuild_status text not null,
    rebuild_action text not null,
    rebuild_reason text not null,

    runtime_allowed boolean not null default false,
    execution_enabled boolean not null default false,

    unique(symbol, strategy, timeframe, trade_source)
);
"""

TRUNCATE = "truncate table rebuild_candidates_v1;"

INSERT = """
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
select
    symbol,
    strategy,
    timeframe,
    trade_source,
    quarantine_status,
    quarantine_reason,
    'PLANNED',
    'REBUILD_CHAINS_AND_ATTRIBUTION',
    'quarantined_reconstruction_artifact',
    false,
    false
from quarantine_reconstruction_artifacts_v1
where quarantine_status='QUARANTINED';
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
    rebuild_reason
from rebuild_candidates_v1
order by symbol, strategy, timeframe;
"""

SUMMARY = """
select
    count(*) total,
    count(*) filter (where rebuild_status='PLANNED') planned
from rebuild_candidates_v1;
"""

def main() -> int:
    print("=== REBUILD CANDIDATES V1 ===")
    print("mode=planning_only")
    print("runtime_allow=0")
    print("execution_enabled=0")

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(DDL)
            cur.execute(TRUNCATE)
            cur.execute(INSERT)
            cur.execute(SUMMARY)
            summary = cur.fetchone()
            cur.execute(REPORT)
            rows = cur.fetchall()
        conn.commit()

    for r in rows:
        print(
            "REBUILD_CANDIDATE_ROW "
            f"symbol={r['symbol']} "
            f"strategy={r['strategy']} "
            f"timeframe={r['timeframe']} "
            f"source={r['trade_source']} "
            f"quarantine={r['quarantine_status']} "
            f"quarantine_reason={r['quarantine_reason']} "
            f"rebuild_status={r['rebuild_status']} "
            f"rebuild_action={r['rebuild_action']} "
            f"rebuild_reason={r['rebuild_reason']} "
            "runtime_allow=0 execution_enabled=0"
        )

    print(
        "REBUILD_CANDIDATES_SUMMARY "
        f"total={summary['total']} "
        f"planned={summary['planned']} "
        "runtime_allow=0 execution_enabled=0"
    )

    print("REBUILD_CANDIDATES_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
