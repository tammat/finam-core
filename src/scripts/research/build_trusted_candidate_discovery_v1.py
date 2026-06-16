#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

DDL = """
create table if not exists trusted_candidate_discovery_v1 (
    id bigserial primary key,
    created_at timestamptz not null default now(),

    symbol text not null,
    strategy text not null,
    timeframe text not null,
    trade_source text not null,

    trades integer not null,
    expectancy numeric not null,
    profit_factor numeric not null,
    winrate numeric not null,

    candidate_rank integer not null,
    discovery_status text not null,

    runtime_allowed boolean not null default false,
    execution_enabled boolean not null default false
);
"""

TRUNCATE = """
truncate table trusted_candidate_discovery_v1;
"""

INSERT = """
insert into trusted_candidate_discovery_v1 (
    symbol,
    strategy,
    timeframe,
    trade_source,
    trades,
    expectancy,
    profit_factor,
    winrate,
    candidate_rank,
    discovery_status,
    runtime_allowed,
    execution_enabled
)
select
    symbol,
    strategy,
    timeframe,
    trade_source,
    trades,
    expectancy,
    profit_factor,
    winrate,
    row_number() over (
        order by
            profit_factor desc,
            expectancy desc,
            trades desc
    ) as candidate_rank,
    'TRUSTED_CANDIDATE',
    false,
    false
from trusted_strategy_statistics_v1
where trusted_status='TRUSTED';
"""

SUMMARY = """
select
    count(*) as candidates
from trusted_candidate_discovery_v1;
"""

REPORT = """
select
    symbol,
    strategy,
    timeframe,
    trade_source,
    trades,
    round(expectancy,6) as expectancy,
    round(profit_factor,4) as profit_factor,
    round(winrate,4) as winrate,
    candidate_rank
from trusted_candidate_discovery_v1
order by candidate_rank;
"""

def main() -> int:
    print("=== TRUSTED CANDIDATE DISCOVERY V1 ===")
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

    candidates = int(summary["candidates"] or 0)

    if candidates == 0:
        print(
            "TRUSTED_DISCOVERY_RESULT "
            "status=NO_TRUSTED_RUNTIME_CANDIDATES "
            "runtime_allow=0 "
            "execution_enabled=0"
        )
    else:
        for r in rows:
            print(
                "TRUSTED_CANDIDATE_ROW "
                f"rank={r['candidate_rank']} "
                f"symbol={r['symbol']} "
                f"strategy={r['strategy']} "
                f"timeframe={r['timeframe']} "
                f"source={r['trade_source']} "
                f"trades={r['trades']} "
                f"expectancy={r['expectancy']} "
                f"profit_factor={r['profit_factor']} "
                f"winrate={r['winrate']} "
                "runtime_allow=0 execution_enabled=0"
            )

    print(
        "TRUSTED_CANDIDATE_DISCOVERY_SUMMARY "
        f"candidates={candidates} "
        "runtime_allow=0 execution_enabled=0"
    )

    print("TRUSTED_CANDIDATE_DISCOVERY_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
