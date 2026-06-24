#!/usr/bin/env python3
import os
import psycopg
from psycopg.rows import dict_row

dsn = os.environ["DATABASE_URL"]

print("=== SIGNAL_FUNNEL_FROM_SIGNALS_TABLE_AUDIT_V1 ===")
print("mode=read_only")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("source_table=signals")

sql = """
select
    coalesce(strategy, 'UNKNOWN') as strategy,
    coalesce(status, 'UNKNOWN') as status,
    coalesce(rejection_reason, 'NO_REJECTION_REASON') as rejection_reason,
    count(*)::int as rows_count
from signals
group by strategy, status, rejection_reason
order by strategy, status, rows_count desc;
"""

summary_sql = """
select
    count(*)::int as total_signals,
    count(*) filter (where status is null)::int as status_null,
    count(*) filter (where strategy is null)::int as strategy_null,
    count(*) filter (where rejection_reason is not null)::int as rejected_with_reason
from signals;
"""

strategy_sql = """
select
    coalesce(strategy, 'UNKNOWN') as strategy,
    count(*)::int as total,
    count(*) filter (where status ilike '%reject%' or rejection_reason is not null)::int as rejected,
    count(*) filter (where status ilike '%accept%' or status ilike '%open%' or status ilike '%created%')::int as accepted_like,
    count(*) filter (where status is null)::int as unknown_status
from signals
group by strategy
order by total desc;
"""

with psycopg.connect(dsn, row_factory=dict_row) as conn:
    with conn.cursor() as cur:
        cur.execute(summary_sql)
        summary = cur.fetchone()

        cur.execute(strategy_sql)
        strategy_rows = cur.fetchall()

        cur.execute(sql)
        reason_rows = cur.fetchall()

print("\nFUNNEL_SUMMARY")
print(
    "SUMMARY_ROW "
    f"total_signals={summary['total_signals']} "
    f"strategy_null={summary['strategy_null']} "
    f"status_null={summary['status_null']} "
    f"rejected_with_reason={summary['rejected_with_reason']}"
)

print("\nSTRATEGY_FUNNEL_ROWS")
for r in strategy_rows:
    total = int(r["total"] or 0)
    rejected = int(r["rejected"] or 0)
    reject_rate = rejected / total if total else 0.0
    print(
        "STRATEGY_FUNNEL_ROW "
        f"strategy={str(r['strategy']).replace(' ', '_')} "
        f"total={total} "
        f"rejected={rejected} "
        f"accepted_like={int(r['accepted_like'] or 0)} "
        f"unknown_status={int(r['unknown_status'] or 0)} "
        f"reject_rate={reject_rate:.4f}"
    )

print("\nREJECTION_REASON_ROWS")
for r in reason_rows:
    print(
        "REJECTION_REASON_ROW "
        f"strategy={str(r['strategy']).replace(' ', '_')} "
        f"status={str(r['status']).replace(' ', '_')} "
        f"reason={str(r['rejection_reason']).replace(' ', '_')} "
        f"rows={int(r['rows_count'] or 0)}"
    )

print("\nFUNNEL_INTERPRETATION")
print("if most rows rejected before intent -> strategy/filter problem")
print("if many UNKNOWN status -> telemetry/schema problem")
print("if accepted_like high but no edge -> entry/exit/PnL problem")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("VERDICT=SIGNAL_FUNNEL_FROM_SIGNALS_TABLE_AUDIT_READY")
