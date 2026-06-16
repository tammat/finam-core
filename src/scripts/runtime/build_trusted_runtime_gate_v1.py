#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

DDL = """
create table if not exists trusted_runtime_gate_v1 (
    id bigserial primary key,
    created_at timestamptz not null default now(),

    symbol text not null,
    strategy text not null,
    timeframe text not null,
    trade_source text not null,

    gate_status text not null,
    gate_reason text not null,

    allow_promotion boolean not null,
    allow_paper_runtime boolean not null,
    allow_real_runtime boolean not null,

    runtime_allowed boolean not null default false,
    execution_enabled boolean not null default false,

    unique(symbol,strategy,timeframe,trade_source)
);
"""

TRUNCATE = """
truncate table trusted_runtime_gate_v1;
"""

INSERT_TRUSTED = """
insert into trusted_runtime_gate_v1 (
    symbol,
    strategy,
    timeframe,
    trade_source,
    gate_status,
    gate_reason,
    allow_promotion,
    allow_paper_runtime,
    allow_real_runtime,
    runtime_allowed,
    execution_enabled
)
select
    symbol,
    strategy,
    timeframe,
    trade_source,
    'OPEN',
    'trusted_candidate',
    true,
    true,
    false,
    false,
    false
from trusted_candidate_discovery_v1;
"""

INSERT_BLOCKED = """
insert into trusted_runtime_gate_v1 (
    symbol,
    strategy,
    timeframe,
    trade_source,
    gate_status,
    gate_reason,
    allow_promotion,
    allow_paper_runtime,
    allow_real_runtime,
    runtime_allowed,
    execution_enabled
)
select
    t.symbol,
    t.strategy,
    t.timeframe,
    t.trade_source,
    'BLOCKED',
    t.trusted_reason,
    false,
    false,
    false,
    false,
    false
from trusted_strategy_statistics_v1 t
where not exists (
    select 1
    from trusted_candidate_discovery_v1 c
    where c.symbol=t.symbol
      and c.strategy=t.strategy
      and c.timeframe=t.timeframe
      and c.trade_source=t.trade_source
);
"""

SUMMARY = """
select
    count(*) total,
    count(*) filter (where gate_status='OPEN') open_rows,
    count(*) filter (where gate_status='BLOCKED') blocked_rows
from trusted_runtime_gate_v1;
"""

REPORT = """
select
    symbol,
    strategy,
    timeframe,
    gate_status,
    gate_reason,
    allow_promotion,
    allow_paper_runtime,
    allow_real_runtime
from trusted_runtime_gate_v1
order by gate_status, symbol, strategy;
"""

def main() -> int:
    print("=== TRUSTED RUNTIME GATE V1 ===")
    print("mode=fail_closed")
    print("runtime_allow=0")
    print("execution_enabled=0")

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(DDL)
            cur.execute(TRUNCATE)
            cur.execute(INSERT_TRUSTED)
            cur.execute(INSERT_BLOCKED)

            cur.execute(SUMMARY)
            summary = cur.fetchone()

            cur.execute(REPORT)
            rows = cur.fetchall()

        conn.commit()

    for r in rows:
        print(
            "TRUSTED_RUNTIME_GATE_ROW "
            f"symbol={r['symbol']} "
            f"strategy={r['strategy']} "
            f"timeframe={r['timeframe']} "
            f"status={r['gate_status']} "
            f"reason={r['gate_reason']} "
            f"promotion={r['allow_promotion']} "
            f"paper={r['allow_paper_runtime']} "
            f"real={r['allow_real_runtime']}"
        )

    print(
        "TRUSTED_RUNTIME_GATE_SUMMARY "
        f"total={summary['total']} "
        f"open={summary['open_rows']} "
        f"blocked={summary['blocked_rows']}"
    )

    print("TRUSTED_RUNTIME_GATE_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
