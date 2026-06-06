#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2


def conn():
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg2.connect(dsn)


def main() -> None:
    print("=== LOSS CONTRIBUTION ANALYSIS V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print()

    with conn() as c:
        with c.cursor() as cur:
            cur.execute("""
                select
                    count(*) as trades,
                    sum(net_pnl) as net_pnl,
                    sum(case when net_pnl < 0 then net_pnl else 0 end) as gross_loss,
                    sum(case when net_pnl > 0 then net_pnl else 0 end) as gross_profit,
                    count(*) filter (where coalesce(strategy, '') = '' or strategy='unknown') as unknown_strategy_rows
                from closed_trades
                where net_pnl is not null;
            """)
            trades, net_pnl, gross_loss, gross_profit, unknown_strategy_rows = cur.fetchone()

            trades = int(trades or 0)
            net_pnl = float(net_pnl or 0)
            gross_loss = float(gross_loss or 0)
            gross_profit = float(gross_profit or 0)
            unknown_strategy_rows = int(unknown_strategy_rows or 0)

            print(
                f"SUMMARY trades={trades} net_pnl={net_pnl:.8f} "
                f"gross_loss={gross_loss:.8f} gross_profit={gross_profit:.8f} "
                f"unknown_strategy_rows={unknown_strategy_rows}"
            )

            if trades == 0 or gross_loss == 0:
                print("VERDICT=INSUFFICIENT_DATA")
                return

            total_loss_abs = abs(gross_loss)

            print()
            print("LOSS_BY_SYMBOL")
            cur.execute("""
                select
                    symbol,
                    count(*) as trades,
                    sum(net_pnl) as net_pnl,
                    sum(case when net_pnl < 0 then net_pnl else 0 end) as loss_pnl,
                    avg(case when net_pnl < 0 then net_pnl end) as avg_loss,
                    min(net_pnl) as max_loss
                from closed_trades
                where net_pnl is not null
                group by symbol
                order by loss_pnl asc nulls last
                limit 30;
            """)
            for symbol, tr, sym_net, loss_pnl, avg_loss, max_loss in cur.fetchall():
                loss_pnl_f = float(loss_pnl or 0)
                contribution = abs(loss_pnl_f) / total_loss_abs if total_loss_abs else 0
                print(
                    f"SYMBOL_ROW symbol={symbol} trades={tr} net_pnl={float(sym_net or 0):.8f} "
                    f"loss_pnl={loss_pnl_f:.8f} contribution={contribution:.4f} "
                    f"avg_loss={float(avg_loss or 0):.8f} max_loss={float(max_loss or 0):.8f}"
                )

            print()
            print("LOSS_BY_STRATEGY")
            cur.execute("""
                select
                    coalesce(nullif(strategy,''),'unknown') as strategy,
                    count(*) as trades,
                    sum(net_pnl) as net_pnl,
                    sum(case when net_pnl < 0 then net_pnl else 0 end) as loss_pnl,
                    min(net_pnl) as max_loss
                from closed_trades
                where net_pnl is not null
                group by coalesce(nullif(strategy,''),'unknown')
                order by loss_pnl asc nulls last
                limit 30;
            """)
            for strategy, tr, strat_net, loss_pnl, max_loss in cur.fetchall():
                loss_pnl_f = float(loss_pnl or 0)
                contribution = abs(loss_pnl_f) / total_loss_abs if total_loss_abs else 0
                print(
                    f"STRATEGY_ROW strategy={strategy} trades={tr} "
                    f"net_pnl={float(strat_net or 0):.8f} loss_pnl={loss_pnl_f:.8f} "
                    f"contribution={contribution:.4f} max_loss={float(max_loss or 0):.8f}"
                )

            print()
            print("LOSS_BY_EXIT_REASON")
            cur.execute("""
                select
                    coalesce(
                        payload->>'exit_reason',
                        payload->'exit_payload'->>'exit_reason',
                        payload->'exit_payload'->>'reason',
                        payload->>'reason',
                        'UNKNOWN'
                    ) as exit_reason,
                    count(*) as trades,
                    sum(net_pnl) as net_pnl,
                    sum(case when net_pnl < 0 then net_pnl else 0 end) as loss_pnl,
                    min(net_pnl) as max_loss
                from closed_trades
                where net_pnl is not null
                group by 1
                order by loss_pnl asc nulls last
                limit 30;
            """)
            for reason, tr, reason_net, loss_pnl, max_loss in cur.fetchall():
                loss_pnl_f = float(loss_pnl or 0)
                contribution = abs(loss_pnl_f) / total_loss_abs if total_loss_abs else 0
                print(
                    f"EXIT_REASON_ROW reason={reason} trades={tr} "
                    f"net_pnl={float(reason_net or 0):.8f} loss_pnl={loss_pnl_f:.8f} "
                    f"contribution={contribution:.4f} max_loss={float(max_loss or 0):.8f}"
                )

            print()
            print("LOSS_BY_HOLDING_BUCKET")
            cur.execute("""
                with base as (
                    select
                        net_pnl,
                        extract(epoch from (
                            coalesce(closed_at, exit_ts, created_at)
                            -
                            coalesce(opened_at, entry_ts, created_at)
                        )) / 60.0 as hold_min
                    from closed_trades
                    where net_pnl is not null
                )
                select
                    case
                        when hold_min is null then 'UNKNOWN'
                        when hold_min < 5 then '0_5_MIN'
                        when hold_min < 30 then '5_30_MIN'
                        when hold_min < 120 then '30_120_MIN'
                        when hold_min < 480 then '2_8_HOURS'
                        else '8H_PLUS'
                    end as hold_bucket,
                    count(*) as trades,
                    sum(net_pnl) as net_pnl,
                    sum(case when net_pnl < 0 then net_pnl else 0 end) as loss_pnl,
                    min(net_pnl) as max_loss
                from base
                group by 1
                order by loss_pnl asc nulls last;
            """)
            for bucket, tr, bucket_net, loss_pnl, max_loss in cur.fetchall():
                loss_pnl_f = float(loss_pnl or 0)
                contribution = abs(loss_pnl_f) / total_loss_abs if total_loss_abs else 0
                print(
                    f"HOLD_BUCKET_ROW bucket={bucket} trades={tr} "
                    f"net_pnl={float(bucket_net or 0):.8f} loss_pnl={loss_pnl_f:.8f} "
                    f"contribution={contribution:.4f} max_loss={float(max_loss or 0):.8f}"
                )

            print()
            print("PARETO_LOSS_CONCENTRATION")
            cur.execute("""
                select net_pnl
                from closed_trades
                where net_pnl < 0
                order by net_pnl asc;
            """)
            losses = [float(r[0]) for r in cur.fetchall()]
            for n in (5, 10, 20, 50, 100):
                top_loss = sum(losses[:n])
                share = abs(top_loss) / total_loss_abs if total_loss_abs else 0
                print(f"PARETO_ROW top_n={n} loss_sum={top_loss:.8f} loss_share={share:.4f}")

            print()
            print("TOP_50_LOSSES")
            cur.execute("""
                select
                    id,
                    symbol,
                    coalesce(nullif(strategy,''),'unknown') as strategy,
                    side,
                    timeframe,
                    net_pnl,
                    coalesce(opened_at, entry_ts, created_at) as entry_ts,
                    coalesce(closed_at, exit_ts, created_at) as exit_ts,
                    coalesce(
                        payload->>'exit_reason',
                        payload->'exit_payload'->>'exit_reason',
                        payload->'exit_payload'->>'reason',
                        payload->>'reason',
                        'UNKNOWN'
                    ) as exit_reason
                from closed_trades
                where net_pnl is not null
                order by net_pnl asc
                limit 50;
            """)
            for row in cur.fetchall():
                trade_id, symbol, strategy, side, timeframe, pnl, entry_ts, exit_ts, reason = row
                print(
                    f"TOP_LOSS_ROW id={trade_id} symbol={symbol} strategy={strategy} "
                    f"side={side} timeframe={timeframe} net_pnl={float(pnl):.8f} "
                    f"entry_ts={entry_ts} exit_ts={exit_ts} exit_reason={reason}"
                )

    print()
    print("VERDICT=OK")


if __name__ == "__main__":
    main()
