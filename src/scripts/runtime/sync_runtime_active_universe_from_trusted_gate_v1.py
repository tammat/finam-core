#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

DDL = """
create table if not exists trusted_runtime_active_universe_sync_v1 (
    id bigserial primary key,
    created_at timestamptz not null default now(),

    symbol text not null,
    strategy text not null,
    timeframe text not null,

    previous_enabled boolean,
    new_enabled boolean not null,

    sync_action text not null,
    sync_reason text not null,

    runtime_allowed boolean not null default false,
    execution_enabled boolean not null default false
);
"""

OPEN_GATE = """
select
    symbol,
    strategy,
    timeframe
from trusted_runtime_gate_v1
where gate_status='OPEN'
  and coalesce(allow_paper_runtime,false)=true;
"""

ACTIVE_ROWS = """
select
    symbol,
    strategy,
    timeframe,
    coalesce(is_enabled,true) as is_enabled
from runtime_active_universe;
"""

DISABLE_UNTRUSTED = """
update runtime_active_universe r
set
    is_enabled=false,
    updated_at=now()
where not exists (
    select 1
    from trusted_runtime_gate_v1 g
    where g.symbol=r.symbol
      and g.strategy=r.strategy
      and g.timeframe=r.timeframe
      and g.gate_status='OPEN'
      and coalesce(g.allow_paper_runtime,false)=true
);
"""

INSERT_AUDIT = """
insert into trusted_runtime_active_universe_sync_v1 (
    symbol,
    strategy,
    timeframe,
    previous_enabled,
    new_enabled,
    sync_action,
    sync_reason,
    runtime_allowed,
    execution_enabled
)
select
    r.symbol,
    r.strategy,
    r.timeframe,
    coalesce(r.is_enabled,true) as previous_enabled,
    false as new_enabled,
    'DISABLE',
    'trusted_runtime_gate_not_open',
    false,
    false
from runtime_active_universe r
where coalesce(r.is_enabled,true)=true
  and not exists (
    select 1
    from trusted_runtime_gate_v1 g
    where g.symbol=r.symbol
      and g.strategy=r.strategy
      and g.timeframe=r.timeframe
      and g.gate_status='OPEN'
      and coalesce(g.allow_paper_runtime,false)=true
  );
"""

SUMMARY = """
select
    count(*) as active_after
from runtime_active_universe
where coalesce(is_enabled,true)=true;
"""

REPORT = """
select
    symbol,
    strategy,
    timeframe,
    is_enabled
from runtime_active_universe
order by symbol,strategy,timeframe;
"""

def main() -> int:
    print("=== WIRE TRUSTED GATE TO RUNTIME ACTIVE UNIVERSE V1 ===")
    print("mode=fail_closed")
    print("runtime_allow=0")
    print("execution_enabled=0")

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(DDL)
            cur.execute(INSERT_AUDIT)
            cur.execute(DISABLE_UNTRUSTED)
            cur.execute(SUMMARY)
            summary = cur.fetchone()
            cur.execute(REPORT)
            rows = cur.fetchall()
        conn.commit()

    for r in rows:
        print(
            "RUNTIME_ACTIVE_UNIVERSE_ROW "
            f"symbol={r['symbol']} "
            f"strategy={r['strategy']} "
            f"timeframe={r['timeframe']} "
            f"is_enabled={r['is_enabled']}"
        )

    print(
        "TRUSTED_GATE_RUNTIME_UNIVERSE_SUMMARY "
        f"active_after={summary['active_after']} "
        "runtime_allow=0 execution_enabled=0"
    )

    print("WIRE_TRUSTED_GATE_TO_RUNTIME_ACTIVE_UNIVERSE_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
