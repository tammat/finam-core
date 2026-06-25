#!/usr/bin/env python3
import os
import psycopg
from psycopg.rows import dict_row

dsn = os.environ["DATABASE_URL"]

print("=== TIME_STOP_5M_MARKET_BAR_REPLAY_V1 ===")
print("mode=read_only_market_bar_replay")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("source_table=closed_trades")
print("bar_source=market_bars")
print("policy=TIME_STOP_5M")

with psycopg.connect(dsn, row_factory=dict_row) as conn:
    with conn.cursor() as cur:
        cur.execute("""
            select column_name
            from information_schema.columns
            where table_schema='public'
              and table_name='market_bars'
        """)
        mb_cols = {r["column_name"] for r in cur.fetchall()}

        cur.execute("""
            select column_name
            from information_schema.columns
            where table_schema='public'
              and table_name='closed_trades'
        """)
        ct_cols = {r["column_name"] for r in cur.fetchall()}

        bar_ts_col = next((c for c in ["bar_ts", "ts", "timestamp", "time"] if c in mb_cols), None)
        close_col = next((c for c in ["close", "close_price"] if c in mb_cols), None)
        mb_symbol_col = next((c for c in ["symbol", "continuous_symbol"] if c in mb_cols), None)
        ct_symbol_col = next((c for c in ["symbol", "continuous_symbol"] if c in ct_cols), None)
        timeframe_col = "timeframe" if "timeframe" in mb_cols else None

        print("\nSCHEMA_DETECTION")
        print(f"market_bars_ts_col={bar_ts_col or 'NOT_FOUND'}")
        print(f"market_bars_close_col={close_col or 'NOT_FOUND'}")
        print(f"market_bars_symbol_col={mb_symbol_col or 'NOT_FOUND'}")
        print(f"closed_trades_symbol_col={ct_symbol_col or 'NOT_FOUND'}")
        print(f"market_bars_timeframe_col={timeframe_col or 'NOT_FOUND'}")

        if not all([bar_ts_col, close_col, mb_symbol_col, ct_symbol_col]):
            print("\nVERDICT=TIME_STOP_5M_MARKET_BAR_REPLAY_SCHEMA_ONLY")
            raise SystemExit(0)

        tf_filter = ""
        if timeframe_col:
            tf_filter = f"and upper(mb.{timeframe_col}::text) in ('M1','1M','1','MIN1')"

        sql = f"""
        with base as (
            select
                row_number() over (order by ct.entry_ts, ct.exit_ts)::text as trade_id,
                ct.{ct_symbol_col}::text as symbol,
                ct.entry_ts,
                ct.exit_ts,
                ct.entry_price::numeric as entry_price,
                ct.exit_price::numeric as real_exit_price,
                ct.gross_pnl::numeric as real_gross_pnl,
                ct.net_pnl::numeric as real_net_pnl,
                coalesce(ct.commission, 0)::numeric as commission,
                ct.entry_ts + interval '5 minutes' as target_exit_ts
            from closed_trades ct
            where ct.entry_ts is not null
              and ct.exit_ts is not null
              and ct.entry_price is not null
              and ct.exit_price is not null
              and ct.gross_pnl is not null
              and ct.net_pnl is not null
              and ct.{ct_symbol_col} is not null
        ),
        matched as (
            select
                b.*,
                mb.{bar_ts_col} as virtual_exit_ts,
                mb.{close_col}::numeric as virtual_exit_price
            from base b
            left join lateral (
                select mb.{bar_ts_col}, mb.{close_col}
                from market_bars mb
                where mb.{mb_symbol_col}::text = b.symbol
                  and mb.{bar_ts_col} >= b.target_exit_ts
                  and mb.{bar_ts_col} <= b.target_exit_ts + interval '10 minutes'
                  {tf_filter}
                order by mb.{bar_ts_col}
                limit 1
            ) mb on true
        ),
        calc as (
            select
                *,
                case
                    when virtual_exit_price is null then null
                    when real_exit_price = entry_price then null
                    when real_gross_pnl * (real_exit_price - entry_price) >= 0 then 1
                    else -1
                end as direction_factor,
                case
                    when real_exit_price = entry_price then null
                    else abs(real_gross_pnl / (real_exit_price - entry_price))
                end as pnl_per_price
            from matched
        ),
        replay as (
            select
                *,
                case
                    when virtual_exit_price is null or direction_factor is null or pnl_per_price is null then null
                    else direction_factor * (virtual_exit_price - entry_price) * pnl_per_price
                end as virtual_gross_pnl
            from calc
        )
        select
            count(*)::int as trades_total,
            count(*) filter (where virtual_exit_price is not null)::int as replayed,
            count(*) filter (where virtual_exit_price is null)::int as no_bar,
            count(*) filter (where virtual_gross_pnl - commission > 0)::int as wins,
            count(*) filter (where virtual_gross_pnl - commission <= 0)::int as losses,
            avg(virtual_gross_pnl - commission) as expectancy,
            sum(virtual_gross_pnl) as gross_pnl,
            sum(commission) as commission,
            sum(virtual_gross_pnl - commission) as net_pnl,
            case
                when abs(sum(least(virtual_gross_pnl - commission,0))) > 0
                then sum(greatest(virtual_gross_pnl - commission,0)) / abs(sum(least(virtual_gross_pnl - commission,0)))
                else null
            end as profit_factor
        from replay
        where virtual_gross_pnl is not null;
        """

        cur.execute(sql)
        r = cur.fetchone()

print("\nREPLAY_SCORECARD")
trades = int(r["replayed"] or 0)
wins = int(r["wins"] or 0)
print(
    "TIME_STOP_5M_ROW "
    f"trades_total={int(r['trades_total'] or 0)} "
    f"replayed={trades} "
    f"no_bar={int(r['no_bar'] or 0)} "
    f"wins={wins} "
    f"losses={int(r['losses'] or 0)} "
    f"winrate={(wins / trades if trades else 0):.4f} "
    f"profit_factor={float(r['profit_factor'] or 0):.4f} "
    f"expectancy={float(r['expectancy'] or 0):.6f} "
    f"gross_pnl={float(r['gross_pnl'] or 0):.6f} "
    f"commission={float(r['commission'] or 0):.6f} "
    f"net_pnl={float(r['net_pnl'] or 0):.6f}"
)

print("\nVERDICT=TIME_STOP_5M_MARKET_BAR_REPLAY_READY")
