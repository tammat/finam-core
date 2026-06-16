#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

DDL = """
create table if not exists quarantine_reconstruction_artifacts_v1 (
    id bigserial primary key,
    created_at timestamptz not null default now(),

    symbol text not null,
    strategy text not null,
    timeframe text not null,
    trade_source text not null,

    quarantine_reason text not null,
    quarantine_status text not null,

    runtime_allowed boolean not null default false,
    execution_enabled boolean not null default false,

    unique(symbol,strategy,timeframe,trade_source)
);
"""

TRUNCATE = """
truncate table quarantine_reconstruction_artifacts_v1;
"""

INSERT = """
insert into quarantine_reconstruction_artifacts_v1 (
    symbol,
    strategy,
    timeframe,
    trade_source,
    quarantine_reason,
    quarantine_status,
    runtime_allowed,
    execution_enabled
)
select
    symbol,
    strategy,
    timeframe,
    trade_source,
    trusted_reason,
    'QUARANTINED',
    false,
    false
from trusted_strategy_statistics_v1
where trusted_reason='identity_suspect';
"""

SUMMARY = """
select
    count(*) total,
    count(*) filter (
        where quarantine_status='QUARANTINED'
    ) quarantined
from quarantine_reconstruction_artifacts_v1;
"""

REPORT = """
select
    symbol,
    strategy,
    timeframe,
    trade_source,
    quarantine_reason,
    quarantine_status
from quarantine_reconstruction_artifacts_v1
order by symbol,strategy,timeframe;
"""

def main() -> int:
    print("=== QUARANTINE RECONSTRUCTION ARTIFACTS V1 ===")
    print("mode=fail_closed")
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
            "QUARANTINE_ROW "
            f"symbol={r['symbol']} "
            f"strategy={r['strategy']} "
            f"timeframe={r['timeframe']} "
            f"source={r['trade_source']} "
            f"reason={r['quarantine_reason']} "
            f"status={r['quarantine_status']} "
            "runtime_allow=0 execution_enabled=0"
        )

    print(
        "QUARANTINE_SUMMARY "
        f"total={summary['total']} "
        f"quarantined={summary['quarantined']} "
        "runtime_allow=0 execution_enabled=0"
    )

    print("QUARANTINE_RECONSTRUCTION_ARTIFACTS_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
