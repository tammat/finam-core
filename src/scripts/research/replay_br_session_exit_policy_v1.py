#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2

from finam_core.exits.br_session_exit_policy import BrSessionExitPolicy


def profit_factor(values):
    gp = sum(v for v in values if v > 0)
    gl = abs(sum(v for v in values if v < 0))
    return None if gl == 0 else gp / gl


def print_metrics(label: str, values: list[float]) -> None:
    trades = len(values)
    net = sum(values)
    wins = sum(1 for v in values if v > 0)
    expectancy = net / trades if trades else 0.0
    winrate = wins / trades if trades else 0.0
    pf = profit_factor(values)

    print(
        f"{label} trades={trades} net_pnl={net:.8f} "
        f"expectancy={expectancy:.8f} winrate={winrate:.4f} "
        f"profit_factor={'None' if pf is None else f'{pf:.8f}'}"
    )


def main() -> None:
    dsn = os.environ["DATABASE_URL"]

    print("=== REPLAY BR SESSION EXIT POLICY V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print()

    sql = """
    with clean_br as (
        select
            ct.id,
            ct.symbol,
            ct.net_pnl,
            ct.entry_price,
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
            b.close
        from clean_br t
        join market_bars b
          on b.symbol = t.symbol
         and b.timeframe = 'M5'
         and b.ts >= t.entry_ts
         and b.ts <= t.exit_ts
    ),
    session_exit as (
        select distinct on (t.id)
            t.id,
            b.ts as session_exit_ts,
            b.close as session_exit_close
        from clean_br t
        join bars b on b.trade_id = t.id
        where (b.ts at time zone 'Europe/Moscow')::time <= time '23:45'
        order by t.id, b.ts desc
    )
    select
        t.id,
        t.symbol,
        t.net_pnl,
        t.entry_price,
        t.entry_ts,
        t.exit_ts,
        s.session_exit_ts,
        s.session_exit_close,
        case
            when s.session_exit_close is null then t.net_pnl
            else s.session_exit_close - t.entry_price
        end as session_policy_pnl
    from clean_br t
    left join session_exit s on s.id = t.id
    order by t.id;
    """

    with psycopg2.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()

    if not rows:
        print("VERDICT=NO_DATA")
        return

    policy = BrSessionExitPolicy()

    actual_values = []
    session_values = []

    print("TRADE_ROWS")
    for (
        trade_id,
        symbol,
        actual_pnl,
        entry_price,
        entry_ts,
        exit_ts,
        session_exit_ts,
        session_exit_close,
        session_policy_pnl,
    ) in rows:
        actual = float(actual_pnl or 0)
        session_pnl = float(session_policy_pnl or 0)

        actual_values.append(actual)
        session_values.append(session_pnl)

        decision = policy.evaluate(
            symbol=symbol,
            position_open=True,
            current_ts=session_exit_ts or exit_ts,
        )

        print(
            f"TRADE_ROW id={trade_id} symbol={symbol} "
            f"actual_pnl={actual:.8f} session_pnl={session_pnl:.8f} "
            f"entry_ts={entry_ts} actual_exit_ts={exit_ts} "
            f"session_exit_ts={session_exit_ts} "
            f"decision={int(decision.should_exit)} reason={decision.reason}"
        )

    print()
    print("SUMMARY")
    print_metrics("BASELINE_HISTORICAL_TIME_EXIT", actual_values)
    print_metrics("BR_SESSION_EXIT_V1", session_values)

    delta = sum(session_values) - sum(actual_values)
    print(f"DELTA_NET_PNL={delta:.8f}")

    pf_session = profit_factor(session_values)
    verdict = (
        "VALIDATED"
        if len(session_values) >= 30
        and sum(session_values) > 0
        and (sum(session_values) / len(session_values)) > 0
        and pf_session is not None
        and pf_session > 1.10
        else "NOT_VALIDATED"
    )

    print(f"VERDICT={verdict}")


if __name__ == "__main__":
    main()
