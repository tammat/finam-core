#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg
from psycopg.rows import dict_row

SYMBOLS = ("GDU6@RTSX", "GLU6@RTSX")
CUTOFF_HOUR_MSK = 19

print("=== GOLD_RUNTIME_SESSION_GUARD_APPLY_DRY_RUN_V1 ===")
print("mode=apply_dry_run")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("paper_orders=0")

dsn = os.environ["DATABASE_URL"]

sql = """
with base as (
    select
        symbol,
        signal_ts,
        signal_ts at time zone 'Europe/Moscow' as signal_msk,
        extract(hour from signal_ts at time zone 'Europe/Moscow')::int as hour_msk,
        status,
        return_pct
    from analytics_rs_bottom_runtime_dry_run_v1
    where symbol = any(%s)
      and status in ('SUCCESS','FAILURE')
      and return_pct is not null
)
select
    symbol,
    case
        when hour_msk >= %s then 'BLOCK_EVENING_SESSION'
        else 'ALLOW_RESEARCH_SHADOW'
    end as guard_decision,
    count(*)::int as rows_total,
    count(*) filter (where return_pct > 0)::int as wins,
    count(*) filter (where return_pct <= 0)::int as losses,
    avg(return_pct) as avg_return,
    sum(return_pct) as total_return,
    min(signal_ts) as first_signal_ts,
    max(signal_ts) as last_signal_ts
from base
group by symbol, guard_decision
order by symbol, guard_decision
"""

with psycopg.connect(dsn, row_factory=dict_row) as conn:
    with conn.cursor() as cur:
        cur.execute(sql, (list(SYMBOLS), CUTOFF_HOUR_MSK))
        rows = cur.fetchall()

print("\nAPPLY_DRY_RUN_ROWS")

allow_rows = 0
blocked_rows = 0

for r in rows:
    if r["guard_decision"] == "ALLOW_RESEARCH_SHADOW":
        allow_rows += int(r["rows_total"] or 0)
    else:
        blocked_rows += int(r["rows_total"] or 0)

    print(
        "APPLY_ROW "
        f"symbol={r['symbol']} "
        f"guard_decision={r['guard_decision']} "
        f"rows_total={r['rows_total']} "
        f"wins={r['wins']} "
        f"losses={r['losses']} "
        f"avg_return={float(r['avg_return'] or 0):.4f} "
        f"total_return={float(r['total_return'] or 0):.4f}"
    )

print("\nAPPLY_DRY_RUN_SUMMARY")
print(f"allow_rows={allow_rows}")
print(f"blocked_rows={blocked_rows}")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("paper_orders=0")
print("VERDICT=GOLD_RUNTIME_SESSION_GUARD_APPLY_DRY_RUN_READY")
