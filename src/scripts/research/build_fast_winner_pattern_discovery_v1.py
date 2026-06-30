#!/usr/bin/env python3
import os
import psycopg
from psycopg.rows import dict_row

dsn = os.environ["DATABASE_URL"]

print("=== FAST_WINNER_PATTERN_DISCOVERY_V1 ===")
print("mode=read_only_discovery")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("source_table=closed_trades")
print("goal=compare_fast_winners_vs_other_trades")

sql = """
with base as (
    select
        coalesce(symbol, 'UNKNOWN') as symbol,
        coalesce(trade_source, 'UNKNOWN') as trade_source,
        coalesce(entry_regime, 'UNKNOWN') as entry_regime,
        coalesce(exit_regime, 'UNKNOWN') as exit_regime,
        entry_ts,
        exit_ts,
        entry_price::numeric as entry_price,
        exit_price::numeric as exit_price,
        gross_pnl::numeric as gross_pnl,
        net_pnl::numeric as net_pnl,
        coalesce(commission, 0)::numeric as commission,
        extract(epoch from (exit_ts - entry_ts)) / 60.0 as holding_minutes,
        abs(exit_price::numeric - entry_price::numeric) as abs_price_move,
        case
            when entry_price::numeric <> 0
            then abs(exit_price::numeric - entry_price::numeric) / abs(entry_price::numeric)
            else null
        end as abs_move_pct
    from closed_trades
    where entry_ts is not null
      and exit_ts is not null
      and entry_price is not null
      and exit_price is not null
      and net_pnl is not null
),
labeled as (
    select
        *,
        case
            when net_pnl > 0 and holding_minutes < 5 then 'FAST_WINNER'
            when net_pnl <= 0 and holding_minutes < 5 then 'FAST_LOSER'
            when net_pnl > 0 and holding_minutes >= 5 then 'SLOW_WINNER'
            else 'SLOW_LOSER'
        end as pattern_class
    from base
),
agg_class as (
    select
        pattern_class,
        count(*)::int as trades,
        count(*) filter (where net_pnl > 0)::int as wins,
        count(*) filter (where net_pnl <= 0)::int as losses,
        avg(net_pnl) as expectancy,
        sum(gross_pnl) as gross_pnl,
        sum(commission) as commission,
        sum(net_pnl) as net_pnl,
        avg(holding_minutes) as avg_holding_minutes,
        percentile_cont(0.5) within group (order by holding_minutes) as median_holding_minutes,
        avg(abs_price_move) as avg_abs_price_move,
        avg(abs_move_pct) as avg_abs_move_pct,
        case
            when abs(sum(least(net_pnl,0))) > 0
            then sum(greatest(net_pnl,0)) / abs(sum(least(net_pnl,0)))
            else null
        end as profit_factor
    from labeled
    group by pattern_class
),
by_symbol as (
    select
        'SYMBOL' as section,
        pattern_class,
        symbol as bucket,
        count(*)::int as trades,
        sum(net_pnl) as net_pnl,
        avg(net_pnl) as expectancy,
        avg(holding_minutes) as avg_holding_minutes,
        avg(abs_move_pct) as avg_abs_move_pct
    from labeled
    group by pattern_class, symbol
),
by_trade_source as (
    select
        'TRADE_SOURCE' as section,
        pattern_class,
        trade_source as bucket,
        count(*)::int as trades,
        sum(net_pnl) as net_pnl,
        avg(net_pnl) as expectancy,
        avg(holding_minutes) as avg_holding_minutes,
        avg(abs_move_pct) as avg_abs_move_pct
    from labeled
    group by pattern_class, trade_source
),
by_entry_regime as (
    select
        'ENTRY_REGIME' as section,
        pattern_class,
        entry_regime as bucket,
        count(*)::int as trades,
        sum(net_pnl) as net_pnl,
        avg(net_pnl) as expectancy,
        avg(holding_minutes) as avg_holding_minutes,
        avg(abs_move_pct) as avg_abs_move_pct
    from labeled
    group by pattern_class, entry_regime
)
select
    'CLASS' as section,
    pattern_class,
    pattern_class as bucket,
    trades,
    wins,
    losses,
    expectancy,
    gross_pnl,
    commission,
    net_pnl,
    avg_holding_minutes,
    median_holding_minutes,
    avg_abs_price_move,
    avg_abs_move_pct,
    profit_factor
from agg_class

union all

select
    section,
    pattern_class,
    bucket,
    trades,
    null::int as wins,
    null::int as losses,
    expectancy,
    null::numeric as gross_pnl,
    null::numeric as commission,
    net_pnl,
    avg_holding_minutes,
    null::numeric as median_holding_minutes,
    null::numeric as avg_abs_price_move,
    avg_abs_move_pct,
    null::numeric as profit_factor
from by_symbol
where trades >= 3

union all

select
    section,
    pattern_class,
    bucket,
    trades,
    null::int as wins,
    null::int as losses,
    expectancy,
    null::numeric as gross_pnl,
    null::numeric as commission,
    net_pnl,
    avg_holding_minutes,
    null::numeric as median_holding_minutes,
    null::numeric as avg_abs_price_move,
    avg_abs_move_pct,
    null::numeric as profit_factor
from by_trade_source
where trades >= 3

union all

select
    section,
    pattern_class,
    bucket,
    trades,
    null::int as wins,
    null::int as losses,
    expectancy,
    null::numeric as gross_pnl,
    null::numeric as commission,
    net_pnl,
    avg_holding_minutes,
    null::numeric as median_holding_minutes,
    null::numeric as avg_abs_price_move,
    avg_abs_move_pct,
    null::numeric as profit_factor
from by_entry_regime
where trades >= 3

order by section, pattern_class, net_pnl desc nulls last;
"""

with psycopg.connect(dsn, row_factory=dict_row) as conn:
    with conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()

print("\nPATTERN_ROWS")
for r in rows:
    print(
        "PATTERN_ROW "
        f"section={r['section']} "
        f"pattern_class={r['pattern_class']} "
        f"bucket={str(r['bucket']).replace(' ', '_')} "
        f"trades={int(r['trades'] or 0)} "
        f"wins={r['wins']} "
        f"losses={r['losses']} "
        f"profit_factor={float(r['profit_factor'] or 0):.4f} "
        f"expectancy={float(r['expectancy'] or 0):.6f} "
        f"gross_pnl={float(r['gross_pnl'] or 0):.6f} "
        f"commission={float(r['commission'] or 0):.6f} "
        f"net_pnl={float(r['net_pnl'] or 0):.6f} "
        f"avg_holding_minutes={float(r['avg_holding_minutes'] or 0):.2f} "
        f"median_holding_minutes={float(r['median_holding_minutes'] or 0):.2f} "
        f"avg_abs_price_move={float(r['avg_abs_price_move'] or 0):.6f} "
        f"avg_abs_move_pct={float(r['avg_abs_move_pct'] or 0):.8f}"
    )

print("\nDISCOVERY_RULES")
print("if FAST_WINNER concentrated by symbol/source/regime -> candidate_feature_filter")
print("if FAST_WINNER has larger avg_abs_move_pct -> momentum_confirmation_candidate")
print("if FAST_LOSER dominates same buckets -> no simple fast-exit rule")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("VERDICT=FAST_WINNER_PATTERN_DISCOVERY_READY")
