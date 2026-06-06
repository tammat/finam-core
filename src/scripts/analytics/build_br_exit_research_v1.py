#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2


def profit_factor(values):
    gp = sum(v for v in values if v > 0)
    gl = abs(sum(v for v in values if v < 0))
    return None if gl == 0 else gp / gl


def metrics(policy, values):
    trades = len(values)
    net = sum(values)
    exp = net / trades if trades else 0.0
    pf = profit_factor(values)
    wins = sum(1 for v in values if v > 0)
    winrate = wins / trades if trades else 0.0

    return {
        "policy": policy,
        "trades": trades,
        "net_pnl": net,
        "expectancy": exp,
        "profit_factor": pf,
        "winrate": winrate,
    }


def print_policy(row):
    pf = row["profit_factor"]
    print(
        f"EXIT_POLICY_ROW policy={row['policy']} "
        f"trades={row['trades']} "
        f"net_pnl={row['net_pnl']:.8f} "
        f"expectancy={row['expectancy']:.8f} "
        f"winrate={row['winrate']:.4f} "
        f"profit_factor={'None' if pf is None else f'{pf:.8f}'}"
    )


def main():
    dsn = os.environ["DATABASE_URL"]

    print("=== BR EXIT RESEARCH V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("scope=clean_non_quarantined_BR")
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

            max(case when b.rn <= 24 then b.close end) as close_2h,
            max(case when b.rn <= 48 then b.close end) as close_4h,
            max(case when b.rn <= 96 then b.close end) as close_8h,

            max(case
                when (b.ts at time zone 'Europe/Moscow')::time <= time '23:45'
                then b.close
            end) as close_session,

            max(b.high - t.entry_price) as mfe,
            min(b.low - t.entry_price) as mae,

            max(b.high) as max_high,
            min(b.low) as min_low
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

        case when close_2h is null then net_pnl else close_2h - entry_price end as pnl_2h,
        case when close_4h is null then net_pnl else close_4h - entry_price end as pnl_4h,
        case when close_8h is null then net_pnl else close_8h - entry_price end as pnl_8h,
        case when close_session is null then net_pnl else close_session - entry_price end as pnl_session,

        coalesce(mfe, 0) as pnl_mfe,
        coalesce(mae, 0) as pnl_mae,

        case
            when coalesce(max_high - entry_price, -999999) >= 2.0 then 2.0
            when coalesce(min_low - entry_price, 999999) <= -4.0 then -4.0
            else net_pnl
        end as pnl_take2_stop4,

        case
            when coalesce(max_high - entry_price, -999999) >= 3.0 then 3.0
            when coalesce(min_low - entry_price, 999999) <= -5.0 then -5.0
            else net_pnl
        end as pnl_take3_stop5,

        case
            when coalesce(max_high - entry_price, -999999) >= 4.0 then 4.0
            when coalesce(min_low - entry_price, 999999) <= -6.0 then -6.0
            else net_pnl
        end as pnl_take4_stop6

    from agg
    order by id;
    """

    with psycopg2.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()

    if not rows:
        print("VERDICT=NO_DATA")
        return

    policies = {
        "historical_time_exit": [],
        "time_stop_2h": [],
        "time_stop_4h": [],
        "time_stop_8h": [],
        "end_of_session": [],
        "mfe_oracle": [],
        "take2_stop4": [],
        "take3_stop5": [],
        "take4_stop6": [],
    }

    detailed = []

    for row in rows:
        (
            trade_id,
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
            pnl_2h,
            pnl_4h,
            pnl_8h,
            pnl_session,
            pnl_mfe,
            pnl_mae,
            pnl_take2_stop4,
            pnl_take3_stop5,
            pnl_take4_stop6,
        ) = row

        policies["historical_time_exit"].append(float(net_pnl or 0))
        policies["time_stop_2h"].append(float(pnl_2h or 0))
        policies["time_stop_4h"].append(float(pnl_4h or 0))
        policies["time_stop_8h"].append(float(pnl_8h or 0))
        policies["end_of_session"].append(float(pnl_session or 0))
        policies["mfe_oracle"].append(float(pnl_mfe or 0))
        policies["take2_stop4"].append(float(pnl_take2_stop4 or 0))
        policies["take3_stop5"].append(float(pnl_take3_stop5 or 0))
        policies["take4_stop6"].append(float(pnl_take4_stop6 or 0))

        detailed.append(
            (
                trade_id,
                symbol,
                strategy,
                float(net_pnl or 0),
                float(pnl_session or 0),
                float(pnl_8h or 0),
                float(pnl_mfe or 0),
                float(hold_minutes or 0),
                entry_ts,
                exit_ts,
            )
        )

    results = [metrics(policy, values) for policy, values in policies.items()]

    print("BASELINE")
    print_policy(next(r for r in results if r["policy"] == "historical_time_exit"))

    print()
    print("CANDIDATE_EXITS")
    for r in results:
        print_policy(r)

    ranked = sorted(
        results,
        key=lambda r: (
            -999999 if r["profit_factor"] is None else r["profit_factor"],
            r["net_pnl"],
        ),
        reverse=True,
    )

    print()
    print("RANKING")
    for i, r in enumerate(ranked, start=1):
        pf = r["profit_factor"]
        print(
            f"RANK_ROW rank={i} policy={r['policy']} "
            f"net_pnl={r['net_pnl']:.8f} expectancy={r['expectancy']:.8f} "
            f"profit_factor={'None' if pf is None else f'{pf:.8f}'} "
            f"winrate={r['winrate']:.4f}"
        )

    winner = ranked[0]
    print()
    winner_pf = winner["profit_factor"]
    winner_pf_text = "None" if winner_pf is None else f"{winner_pf:.8f}"

    print(
        f"WINNER_POLICY={winner['policy']} "
        f"WINNER_NET_PNL={winner['net_pnl']:.8f} "
        f"WINNER_EXPECTANCY={winner['expectancy']:.8f} "
        f"WINNER_PF={winner_pf_text}"
    )

    print()
    print("TOP_POLICY_IMPROVEMENT_ROWS")
    for (
        trade_id,
        symbol,
        strategy,
        actual,
        session,
        p8h,
        mfe,
        hold_min,
        entry_ts,
        exit_ts,
    ) in sorted(detailed, key=lambda x: x[4] - x[3], reverse=True)[:20]:
        print(
            f"IMPROVEMENT_ROW id={trade_id} symbol={symbol} strategy={strategy} "
            f"actual={actual:.8f} end_session={session:.8f} exit_8h={p8h:.8f} "
            f"mfe={mfe:.8f} session_improvement={session - actual:.8f} "
            f"hold_minutes={hold_min:.2f} entry_ts={entry_ts} exit_ts={exit_ts}"
        )

    print()
    print("VERDICT=OK")


if __name__ == "__main__":
    main()
