#!/usr/bin/env python3

import os
import psycopg2


def pf_expr():
    return """
    case
      when abs(sum(case when net_pnl < 0 then net_pnl else 0 end)) = 0 then null
      else
        sum(case when net_pnl > 0 then net_pnl else 0 end)
        / abs(sum(case when net_pnl < 0 then net_pnl else 0 end))
    end
    """


def main():
    dsn = os.environ["DATABASE_URL"]

    print("=== BR CLEAN LOSS BREAKDOWN V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("scope=clean_non_quarantined_BR")
    print()

    with psycopg2.connect(dsn) as conn:
        with conn.cursor() as cur:

            base_where = """
                ct.net_pnl is not null
                and ct.symbol in ('BRN6@RTSX','BRM6@RTSX')
                and not exists (
                    select 1
                    from research_closed_trades_quarantine q
                    where q.trade_id = ct.id
                )
            """

            cur.execute(f"""
                select
                    count(*) as trades,
                    sum(ct.net_pnl) as net_pnl,
                    sum(case when ct.net_pnl > 0 then ct.net_pnl else 0 end) as gross_profit,
                    abs(sum(case when ct.net_pnl < 0 then ct.net_pnl else 0 end)) as gross_loss,
                    avg(ct.net_pnl) as expectancy,
                    avg(case when ct.net_pnl > 0 then 1 else 0 end) as winrate,
                    {pf_expr()} as profit_factor
                from closed_trades ct
                where {base_where};
            """)

            row = cur.fetchone()
            trades, net_pnl, gp, gl, expectancy, winrate, pf = row

            print(
                f"SUMMARY trades={int(trades or 0)} "
                f"net_pnl={float(net_pnl or 0):.8f} "
                f"gross_profit={float(gp or 0):.8f} "
                f"gross_loss={float(gl or 0):.8f} "
                f"expectancy={float(expectancy or 0):.8f} "
                f"winrate={float(winrate or 0):.4f} "
                f"profit_factor={'None' if pf is None else f'{float(pf):.8f}'}"
            )

            dimensions = [
                ("BY_SYMBOL", "ct.symbol"),
                ("BY_STRATEGY", "coalesce(nullif(ct.strategy,''),'UNKNOWN')"),
                ("BY_SIDE", "coalesce(nullif(ct.side,''),'UNKNOWN')"),
                ("BY_TIMEFRAME", "coalesce(nullif(ct.timeframe,''),'UNKNOWN')"),
                (
                    "BY_EXIT_REASON",
                    """coalesce(
                        ct.payload->>'exit_reason',
                        ct.payload->'exit_payload'->>'exit_reason',
                        ct.payload->'exit_payload'->>'reason',
                        ct.payload->>'reason',
                        'UNKNOWN'
                    )""",
                ),
                (
                    "BY_HOLD_BUCKET",
                    """case
                        when extract(epoch from (
                            coalesce(ct.closed_at, ct.exit_ts, ct.created_at)
                            -
                            coalesce(ct.opened_at, ct.entry_ts, ct.created_at)
                        )) / 60.0 < 5 then '0_5_MIN'
                        when extract(epoch from (
                            coalesce(ct.closed_at, ct.exit_ts, ct.created_at)
                            -
                            coalesce(ct.opened_at, ct.entry_ts, ct.created_at)
                        )) / 60.0 < 30 then '5_30_MIN'
                        when extract(epoch from (
                            coalesce(ct.closed_at, ct.exit_ts, ct.created_at)
                            -
                            coalesce(ct.opened_at, ct.entry_ts, ct.created_at)
                        )) / 60.0 < 120 then '30_120_MIN'
                        when extract(epoch from (
                            coalesce(ct.closed_at, ct.exit_ts, ct.created_at)
                            -
                            coalesce(ct.opened_at, ct.entry_ts, ct.created_at)
                        )) / 60.0 < 480 then '2_8_HOURS'
                        else '8H_PLUS'
                    end""",
                ),
            ]

            for title, expr in dimensions:
                print()
                print(title)

                cur.execute(f"""
                    select
                        {expr} as key,
                        count(*) as trades,
                        sum(ct.net_pnl) as net_pnl,
                        sum(case when ct.net_pnl > 0 then ct.net_pnl else 0 end) as gross_profit,
                        abs(sum(case when ct.net_pnl < 0 then ct.net_pnl else 0 end)) as gross_loss,
                        avg(ct.net_pnl) as expectancy,
                        avg(case when ct.net_pnl > 0 then 1 else 0 end) as winrate,
                        {pf_expr()} as profit_factor
                    from closed_trades ct
                    where {base_where}
                    group by 1
                    order by sum(ct.net_pnl) asc nulls last;
                """)

                for r in cur.fetchall():
                    key, tr, pnl, gross_profit, gross_loss, exp, wr, pfv = r
                    print(
                        f"BREAKDOWN_ROW dimension={title} key={key} "
                        f"trades={int(tr or 0)} "
                        f"net_pnl={float(pnl or 0):.8f} "
                        f"gross_profit={float(gross_profit or 0):.8f} "
                        f"gross_loss={float(gross_loss or 0):.8f} "
                        f"expectancy={float(exp or 0):.8f} "
                        f"winrate={float(wr or 0):.4f} "
                        f"profit_factor={'None' if pfv is None else f'{float(pfv):.8f}'}"
                    )

            print()
            print("TOP_BR_CLEAN_LOSSES")
            cur.execute(f"""
                select
                    ct.id,
                    ct.symbol,
                    coalesce(nullif(ct.strategy,''),'UNKNOWN') as strategy,
                    coalesce(nullif(ct.side,''),'UNKNOWN') as side,
                    coalesce(nullif(ct.timeframe,''),'UNKNOWN') as timeframe,
                    ct.net_pnl,
                    coalesce(ct.opened_at, ct.entry_ts, ct.created_at) as entry_ts,
                    coalesce(ct.closed_at, ct.exit_ts, ct.created_at) as exit_ts,
                    coalesce(
                        ct.payload->>'exit_reason',
                        ct.payload->'exit_payload'->>'exit_reason',
                        ct.payload->'exit_payload'->>'reason',
                        ct.payload->>'reason',
                        'UNKNOWN'
                    ) as exit_reason
                from closed_trades ct
                where {base_where}
                order by ct.net_pnl asc
                limit 30;
            """)

            for r in cur.fetchall():
                trade_id, symbol, strategy, side, timeframe, pnl, entry_ts, exit_ts, reason = r
                print(
                    f"TOP_LOSS_ROW id={trade_id} symbol={symbol} strategy={strategy} "
                    f"side={side} timeframe={timeframe} net_pnl={float(pnl or 0):.8f} "
                    f"entry_ts={entry_ts} exit_ts={exit_ts} exit_reason={reason}"
                )

    print()
    print("VERDICT=OK")


if __name__ == "__main__":
    main()
