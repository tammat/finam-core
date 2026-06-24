#!/usr/bin/env python3
import os
import psycopg
from psycopg.rows import dict_row

dsn = os.environ["DATABASE_URL"]

print("=== ENTRY_EXIT_QUALITY_ROOT_CAUSE_AUDIT_V2 ===")
print("mode=read_only")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("source_table=closed_trades")

sql_by_source = """
with base as (
    select
        coalesce(trade_source, 'UNKNOWN') as bucket,
        gross_pnl::numeric as gross_pnl,
        net_pnl::numeric as net_pnl,
        coalesce(commission, 0)::numeric as commission,
        entry_ts,
        exit_ts,
        extract(epoch from (exit_ts - entry_ts)) / 60.0 as holding_minutes
    from closed_trades
    where net_pnl is not null
),
agg as (
    select
        bucket,
        count(*)::int as trades,
        count(*) filter (where net_pnl > 0)::int as wins,
        count(*) filter (where net_pnl <= 0)::int as losses,
        avg(net_pnl) as expectancy,
        avg(net_pnl) filter (where net_pnl > 0) as avg_win,
        avg(net_pnl) filter (where net_pnl <= 0) as avg_loss,
        sum(gross_pnl) as gross_pnl_total,
        sum(commission) as commission_total,
        sum(net_pnl) as net_pnl_total,
        avg(holding_minutes) as avg_holding_minutes,
        case
            when abs(sum(least(net_pnl,0))) > 0
            then sum(greatest(net_pnl,0)) / abs(sum(least(net_pnl,0)))
            else null
        end as profit_factor
    from base
    group by bucket
)
select * from agg
order by net_pnl_total asc nulls last;
"""

sql_by_regime = """
with base as (
    select
        coalesce(entry_regime, 'UNKNOWN_ENTRY') || '->' || coalesce(exit_regime, 'UNKNOWN_EXIT') as bucket,
        gross_pnl::numeric as gross_pnl,
        net_pnl::numeric as net_pnl,
        coalesce(commission, 0)::numeric as commission,
        extract(epoch from (exit_ts - entry_ts)) / 60.0 as holding_minutes
    from closed_trades
    where net_pnl is not null
),
agg as (
    select
        bucket,
        count(*)::int as trades,
        count(*) filter (where net_pnl > 0)::int as wins,
        count(*) filter (where net_pnl <= 0)::int as losses,
        avg(net_pnl) as expectancy,
        avg(net_pnl) filter (where net_pnl > 0) as avg_win,
        avg(net_pnl) filter (where net_pnl <= 0) as avg_loss,
        sum(gross_pnl) as gross_pnl_total,
        sum(commission) as commission_total,
        sum(net_pnl) as net_pnl_total,
        avg(holding_minutes) as avg_holding_minutes,
        case
            when abs(sum(least(net_pnl,0))) > 0
            then sum(greatest(net_pnl,0)) / abs(sum(least(net_pnl,0)))
            else null
        end as profit_factor
    from base
    group by bucket
)
select * from agg
order by net_pnl_total asc nulls last;
"""

sql_holding = """
with base as (
    select
        case
            when extract(epoch from (exit_ts - entry_ts)) / 60.0 < 5 then 'LT_5_MIN'
            when extract(epoch from (exit_ts - entry_ts)) / 60.0 < 15 then 'LT_15_MIN'
            when extract(epoch from (exit_ts - entry_ts)) / 60.0 < 60 then 'LT_60_MIN'
            when extract(epoch from (exit_ts - entry_ts)) / 60.0 < 240 then 'LT_240_MIN'
            else 'GE_240_MIN'
        end as bucket,
        gross_pnl::numeric as gross_pnl,
        net_pnl::numeric as net_pnl,
        coalesce(commission, 0)::numeric as commission,
        extract(epoch from (exit_ts - entry_ts)) / 60.0 as holding_minutes
    from closed_trades
    where net_pnl is not null
      and entry_ts is not null
      and exit_ts is not null
),
agg as (
    select
        bucket,
        count(*)::int as trades,
        count(*) filter (where net_pnl > 0)::int as wins,
        count(*) filter (where net_pnl <= 0)::int as losses,
        avg(net_pnl) as expectancy,
        avg(net_pnl) filter (where net_pnl > 0) as avg_win,
        avg(net_pnl) filter (where net_pnl <= 0) as avg_loss,
        sum(gross_pnl) as gross_pnl_total,
        sum(commission) as commission_total,
        sum(net_pnl) as net_pnl_total,
        avg(holding_minutes) as avg_holding_minutes,
        case
            when abs(sum(least(net_pnl,0))) > 0
            then sum(greatest(net_pnl,0)) / abs(sum(least(net_pnl,0)))
            else null
        end as profit_factor
    from base
    group by bucket
)
select * from agg
order by net_pnl_total asc nulls last;
"""

def print_rows(section: str, rows):
    print(f"\n{section}")
    for r in rows:
        trades = int(r["trades"] or 0)
        wins = int(r["wins"] or 0)
        winrate = wins / trades if trades else 0.0
        avg_win = float(r["avg_win"] or 0)
        avg_loss = float(r["avg_loss"] or 0)
        commission_total = float(r["commission_total"] or 0)
        gross_total = float(r["gross_pnl_total"] or 0)
        net_total = float(r["net_pnl_total"] or 0)
        fee_drag_ratio = abs(commission_total / gross_total) if gross_total else 0.0

        print(
            "QUALITY_ROW "
            f"section={section} "
            f"bucket={str(r['bucket']).replace(' ', '_')} "
            f"trades={trades} "
            f"wins={wins} "
            f"losses={int(r['losses'] or 0)} "
            f"winrate={winrate:.4f} "
            f"profit_factor={float(r['profit_factor'] or 0):.4f} "
            f"expectancy={float(r['expectancy'] or 0):.6f} "
            f"avg_win={avg_win:.6f} "
            f"avg_loss={avg_loss:.6f} "
            f"gross_pnl={gross_total:.6f} "
            f"commission={commission_total:.6f} "
            f"net_pnl={net_total:.6f} "
            f"fee_drag_ratio={fee_drag_ratio:.6f} "
            f"avg_holding_minutes={float(r['avg_holding_minutes'] or 0):.2f}"
        )

with psycopg.connect(dsn, row_factory=dict_row) as conn:
    with conn.cursor() as cur:
        cur.execute(sql_by_source)
        source_rows = cur.fetchall()

        cur.execute(sql_by_regime)
        regime_rows = cur.fetchall()

        cur.execute(sql_holding)
        holding_rows = cur.fetchall()

print_rows("BY_TRADE_SOURCE", source_rows)
print_rows("BY_REGIME", regime_rows)
print_rows("BY_HOLDING_BUCKET", holding_rows)

print("\nROOT_CAUSE_RULES")
print("if winrate_ok_but_pf_low -> avg_loss_or_exit_problem")
print("if gross_positive_but_net_negative -> commission_drag_problem")
print("if short_holding_negative -> premature_exit_problem")
print("if regime_bucket_negative -> regime_filter_candidate")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("VERDICT=ENTRY_EXIT_QUALITY_ROOT_CAUSE_AUDIT_V2_READY")
