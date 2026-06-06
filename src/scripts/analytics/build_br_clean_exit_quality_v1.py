#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2


def pf(values):
    gp = sum(v for v in values if v > 0)
    gl = abs(sum(v for v in values if v < 0))
    return None if gl == 0 else gp / gl


def line(label, values):
    n = len(values)
    total = sum(values)
    exp = total / n if n else 0.0
    p = pf(values)
    print(
        f"{label} trades={n} net_pnl={total:.8f} "
        f"expectancy={exp:.8f} profit_factor={'None' if p is None else f'{p:.8f}'}"
    )


def main():
    dsn = os.environ["DATABASE_URL"]

    print("=== BR CLEAN EXIT QUALITY V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print()

    sql = """
    with clean_br as (
        select
            ct.id,
            ct.symbol,
            ct.strategy,
            ct.side,
            ct.timeframe,
            ct.net_pnl,
            ct.entry_price,
            ct.exit_price,
            coalesce(ct.opened_at, ct.entry_ts, ct.created_at) as entry_ts,
            coalesce(ct.closed_at, ct.exit_ts, ct.created_at) as exit_ts
        from closed_trades ct
        where ct.net_pnl is not null
          and ct.symbol = 'BRN6@RTSX'
          and not exists (
              select 1
              from research_closed_trades_quarantine q
              where q.trade_id = ct.id
          )
    ),
    bars as (
        select
            t.id as trade_id,
            b.ts,
            b.high,
            b.low,
            b.close,
            row_number() over (partition by t.id order by b.ts asc) as rn
        from clean_br t
        join market_bars b
          on b.symbol = t.symbol
         and b.timeframe = 'M5'
         and b.ts >= t.entry_ts
         and b.ts <= t.exit_ts
    ),
    agg as (
        select
            t.id,
            t.symbol,
            t.strategy,
            t.side,
            t.timeframe,
            t.net_pnl,
            t.entry_price,
            t.exit_price,
            t.entry_ts,
            t.exit_ts,
            extract(epoch from (t.exit_ts - t.entry_ts)) / 60.0 as hold_minutes,
            max(b.high - t.entry_price) as mfe,
            min(b.low - t.entry_price) as mae,
            max(case when b.rn <= 24 then b.close end) as exit_2h_close,
            max(case when b.rn <= 48 then b.close end) as exit_4h_close,
            max(case when b.rn <= 96 then b.close end) as exit_8h_close,
            max(b.close) as best_close,
            min(b.close) as worst_close,
            max(case
                when (b.ts at time zone 'Europe/Moscow')::time <= time '23:45'
                then b.close
            end) as session_close
        from clean_br t
        left join bars b on b.trade_id = t.id
        group by
            t.id, t.symbol, t.strategy, t.side, t.timeframe,
            t.net_pnl, t.entry_price, t.exit_price, t.entry_ts, t.exit_ts
    )
    select
        id,
        symbol,
        strategy,
        side,
        timeframe,
        net_pnl,
        entry_price,
        exit_price,
        entry_ts,
        exit_ts,
        hold_minutes,
        coalesce(mfe, 0) as mfe,
        coalesce(mae, 0) as mae,
        case when exit_2h_close is null then net_pnl else exit_2h_close - entry_price end as pnl_2h,
        case when exit_4h_close is null then net_pnl else exit_4h_close - entry_price end as pnl_4h,
        case when exit_8h_close is null then net_pnl else exit_8h_close - entry_price end as pnl_8h,
        case when session_close is null then net_pnl else session_close - entry_price end as pnl_session,
        coalesce(mfe, 0) as pnl_at_mfe
    from agg
    order by id;
    """

    with psycopg2.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()

    if not rows:
        print("SUMMARY trades=0")
        print("VERDICT=NO_DATA")
        return

    actual = []
    p2h = []
    p4h = []
    p8h = []
    psession = []
    pmfe = []
    giveback = []
    positive_mfe = 0

    detailed = []

    for r in rows:
        (
            trade_id, symbol, strategy, side, timeframe, net_pnl,
            entry_price, exit_price, entry_ts, exit_ts, hold_minutes,
            mfe, mae, pnl_2h, pnl_4h, pnl_8h, pnl_session, pnl_at_mfe
        ) = r

        net = float(net_pnl or 0)
        mfe_f = float(mfe or 0)
        gb = mfe_f - net

        actual.append(net)
        p2h.append(float(pnl_2h or 0))
        p4h.append(float(pnl_4h or 0))
        p8h.append(float(pnl_8h or 0))
        psession.append(float(pnl_session or 0))
        pmfe.append(float(pnl_at_mfe or 0))
        giveback.append(gb)

        if mfe_f > 0:
            positive_mfe += 1

        detailed.append((gb, trade_id, symbol, strategy, net, mfe_f, float(mae or 0), float(hold_minutes or 0), entry_ts, exit_ts))

    print("SUMMARY")
    line("ACTUAL_EXIT", actual)
    print(f"POSITIVE_MFE_TRADES={positive_mfe}")
    print(f"POSITIVE_MFE_RATE={positive_mfe / len(rows):.4f}")
    print(f"TOTAL_GIVEBACK={sum(giveback):.8f}")
    print(f"AVG_GIVEBACK={sum(giveback) / len(giveback):.8f}")
    print()

    print("EXIT_SIMULATION")
    line("EXIT_AFTER_2H", p2h)
    line("EXIT_AFTER_4H", p4h)
    line("EXIT_AFTER_8H", p8h)
    line("EXIT_END_OF_SESSION", psession)
    line("EXIT_AT_MFE", pmfe)
    print()

    print("TOP_GIVEBACK_TRADES")
    for gb, trade_id, symbol, strategy, net, mfe_f, mae_f, hold_min, entry_ts, exit_ts in sorted(detailed, reverse=True)[:20]:
        print(
            f"GIVEBACK_ROW id={trade_id} symbol={symbol} strategy={strategy} "
            f"net_pnl={net:.8f} mfe={mfe_f:.8f} mae={mae_f:.8f} "
            f"giveback={gb:.8f} hold_minutes={hold_min:.2f} "
            f"entry_ts={entry_ts} exit_ts={exit_ts}"
        )

    print()
    print("VERDICT=OK")


if __name__ == "__main__":
    main()
