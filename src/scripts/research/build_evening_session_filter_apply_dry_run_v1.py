#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg
from psycopg.rows import dict_row

SYMBOLS = ("GDU6@RTSX", "GLU6@RTSX")
CUTOFF_HOUR_MSK = 19


def fmt(v):
    if v is None:
        return "NONE"
    return f"{float(v):.4f}"


def decision_for_hour(hour_msk: int) -> str:
    if hour_msk >= CUTOFF_HOUR_MSK:
        return "BLOCK_EVENING_SESSION"
    return "ALLOW_RESEARCH_SHADOW"


dsn = os.environ["DATABASE_URL"]

sql = """
with base as (
    select
        symbol,
        signal_ts,
        created_at,
        status,
        return_pct,
        extract(hour from signal_ts at time zone 'Europe/Moscow')::int as hour_msk,
        signal_ts at time zone 'Europe/Moscow' as signal_msk
    from analytics_rs_bottom_runtime_dry_run_v1
    where symbol = any(%s)
      and status in ('SUCCESS','FAILURE')
      and return_pct is not null
),
planned as (
    select
        *,
        case
            when hour_msk >= %s then 'BLOCK_EVENING_SESSION'
            else 'ALLOW_RESEARCH_SHADOW'
        end as planned_decision
    from base
)
select
    symbol,
    planned_decision,
    count(*)::int as rows_total,
    count(*) filter (where return_pct > 0)::int as wins,
    count(*) filter (where return_pct <= 0)::int as losses,
    avg(return_pct) as avg_return,
    sum(return_pct) as total_return,
    min(signal_ts) as first_signal_ts,
    max(signal_ts) as last_signal_ts
from planned
group by symbol, planned_decision
order by symbol, planned_decision
"""

print("=== EVENING_SESSION_FILTER_APPLY_DRY_RUN_V1 ===")
print("mode=apply_dry_run")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("paper_orders=0")
print(f"symbols={','.join(SYMBOLS)}")
print(f"rule=hour_msk < {CUTOFF_HOUR_MSK} ALLOW_RESEARCH_SHADOW else BLOCK_EVENING_SESSION")

with psycopg.connect(dsn, row_factory=dict_row) as conn:
    with conn.cursor() as cur:
        cur.execute(sql, (list(SYMBOLS), CUTOFF_HOUR_MSK))
        rows = cur.fetchall()

allow_total = 0
block_total = 0

print("\nDRY_RUN_ROWS")
for r in rows:
    decision = r["planned_decision"]
    if decision == "ALLOW_RESEARCH_SHADOW":
        allow_total += int(r["rows_total"] or 0)
    if decision == "BLOCK_EVENING_SESSION":
        block_total += int(r["rows_total"] or 0)

    print(
        "DRY_RUN_ROW "
        f"symbol={r['symbol']} "
        f"planned_decision={decision} "
        f"rows_total={r['rows_total']} "
        f"wins={r['wins']} "
        f"losses={r['losses']} "
        f"avg_return={fmt(r['avg_return'])} "
        f"total_return={fmt(r['total_return'])} "
        f"first_signal_ts={r['first_signal_ts']} "
        f"last_signal_ts={r['last_signal_ts']}"
    )

print("\nDRY_RUN_SUMMARY")
print(f"allow_rows={allow_total}")
print(f"blocked_rows={block_total}")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("paper_orders=0")
print("VERDICT=EVENING_SESSION_FILTER_APPLY_DRY_RUN_READY")
