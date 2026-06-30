#!/usr/bin/env python3
import os
import psycopg
from psycopg.rows import dict_row

dsn = os.environ["DATABASE_URL"]

print("=== ENTRY_EXIT_QUALITY_ROOT_CAUSE_AUDIT_V1 ===")
print("mode=read_only")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("source_table=trades")

candidate_pnl_cols = ["net_pnl", "pnl", "gross_pnl", "realized_pnl", "return_pct"]
candidate_exit_cols = ["exit_reason", "reason", "invalid_reason", "trade_source"]
candidate_time_cols = ["closed_at", "exit_ts", "created_at", "ts", "timestamp"]

with psycopg.connect(dsn, row_factory=dict_row) as conn:
    with conn.cursor() as cur:
        cur.execute("""
            select column_name, data_type
            from information_schema.columns
            where table_schema='public'
              and table_name='trades'
            order by ordinal_position
        """)
        cols = {r["column_name"]: r["data_type"] for r in cur.fetchall()}

        pnl_col = next((c for c in candidate_pnl_cols if c in cols), None)
        exit_col = next((c for c in candidate_exit_cols if c in cols), None)
        time_col = next((c for c in candidate_time_cols if c in cols), None)

        print("\nSCHEMA_DETECTION")
        print(f"pnl_col={pnl_col or 'NOT_FOUND'}")
        print(f"exit_col={exit_col or 'NOT_FOUND'}")
        print(f"time_col={time_col or 'NOT_FOUND'}")

        if pnl_col is None:
            print("\nEXIT_REASON_ROWS")
            print("EXIT_REASON_ROW exit_reason=UNAVAILABLE reason=no_pnl_column_in_trades")
            print("\nVERDICT=ENTRY_EXIT_QUALITY_ROOT_CAUSE_AUDIT_SCHEMA_ONLY")
            raise SystemExit(0)

        exit_expr = f"coalesce({exit_col}, 'UNKNOWN')" if exit_col else "'UNKNOWN'"
        time_expr = time_col if time_col else "null"

        sql = f"""
        with base as (
            select
                coalesce(strategy, 'UNKNOWN') as strategy,
                coalesce(symbol, 'UNKNOWN') as symbol,
                {exit_expr}::text as exit_reason,
                {pnl_col}::numeric as pnl,
                {time_expr} as ts
            from trades
            where {pnl_col} is not null
        )
        select
            exit_reason,
            count(*)::int as trades,
            count(*) filter (where pnl > 0)::int as wins,
            count(*) filter (where pnl <= 0)::int as losses,
            avg(pnl) as expectancy,
            avg(pnl) filter (where pnl > 0) as avg_win,
            avg(pnl) filter (where pnl <= 0) as avg_loss,
            sum(pnl) as gross_pnl,
            count(*) * 0.02 as fee_drag_estimate,
            sum(pnl) - count(*) * 0.02 as net_pnl_estimate,
            case
                when abs(sum(least(pnl,0))) > 0
                then sum(greatest(pnl,0)) / abs(sum(least(pnl,0)))
                else null
            end as profit_factor
        from base
        group by exit_reason
        order by net_pnl_estimate asc nulls last;
        """

        cur.execute(sql)
        rows = cur.fetchall()

print("\nEXIT_REASON_ROWS")
for r in rows:
    trades = int(r["trades"] or 0)
    wins = int(r["wins"] or 0)
    winrate = wins / trades if trades else 0.0

    print(
        "EXIT_REASON_ROW "
        f"exit_reason={str(r['exit_reason']).replace(' ', '_')} "
        f"trades={trades} "
        f"wins={wins} "
        f"losses={int(r['losses'] or 0)} "
        f"winrate={winrate:.4f} "
        f"expectancy={float(r['expectancy'] or 0):.6f} "
        f"avg_win={float(r['avg_win'] or 0):.6f} "
        f"avg_loss={float(r['avg_loss'] or 0):.6f} "
        f"profit_factor={float(r['profit_factor'] or 0):.4f} "
        f"gross_pnl={float(r['gross_pnl'] or 0):.6f} "
        f"fee_drag_estimate={float(r['fee_drag_estimate'] or 0):.6f} "
        f"net_pnl_estimate={float(r['net_pnl_estimate'] or 0):.6f}"
    )

print("\nROOT_CAUSE_RULES")
print("if avg_win small and fee_drag dominates -> movement_amplitude_problem")
print("if specific exit_reason negative -> exit_policy_problem")
print("if winrate ok but net negative -> fee_drag_or_avg_loss_problem")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("VERDICT=ENTRY_EXIT_QUALITY_ROOT_CAUSE_AUDIT_READY")
