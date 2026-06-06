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
    wins = sum(1 for v in values if v > 0)
    gp = sum(v for v in values if v > 0)
    gl = abs(sum(v for v in values if v < 0))
    pf = profit_factor(values)
    expectancy = net / trades if trades else 0.0
    winrate = wins / trades if trades else 0.0
    max_loss = min(values) if values else 0.0

    pf_score = 0.0 if pf is None else min(pf, 3.0)
    score = expectancy * 0.4 + pf_score * 0.4 + winrate * 0.2

    passed = bool(
        trades >= 30
        and net > 0
        and expectancy > 0
        and pf is not None
        and pf > 1.10
    )

    return {
        "policy": policy,
        "trades": trades,
        "net_pnl": net,
        "gross_profit": gp,
        "gross_loss": gl,
        "expectancy": expectancy,
        "profit_factor": pf,
        "winrate": winrate,
        "max_loss": max_loss,
        "score": score,
        "passed": passed,
    }


def print_row(prefix, rank, row):
    pf = row["profit_factor"]
    print(
        f"{prefix} rank={rank} policy={row['policy']} "
        f"trades={row['trades']} net_pnl={row['net_pnl']:.8f} "
        f"gross_profit={row['gross_profit']:.8f} gross_loss={row['gross_loss']:.8f} "
        f"expectancy={row['expectancy']:.8f} "
        f"winrate={row['winrate']:.4f} "
        f"profit_factor={'None' if pf is None else f'{pf:.8f}'} "
        f"max_loss={row['max_loss']:.8f} score={row['score']:.8f} "
        f"passed={int(row['passed'])}"
    )


def main():
    dsn = os.environ["DATABASE_URL"]

    print("=== BR EXIT POLICY CANDIDATE V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("scope=clean_non_quarantined_BR")
    print("selection_rule=trades>=30,pf>1.10,expectancy>0,net_pnl>0")
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
            t.net_pnl,
            t.entry_price,

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
        group by t.id, t.net_pnl, t.entry_price
    )
    select
        id,
        net_pnl,
        entry_price,

        case when close_2h is null then net_pnl else close_2h - entry_price end as pnl_2h,
        case when close_4h is null then net_pnl else close_4h - entry_price end as pnl_4h,
        case when close_8h is null then net_pnl else close_8h - entry_price end as pnl_8h,
        case when close_session is null then net_pnl else close_session - entry_price end as pnl_session,

        coalesce(mfe, 0) as pnl_mfe,

        case
            when coalesce(max_high - entry_price, -999999) >= 1.5 then 1.5
            when coalesce(min_low - entry_price, 999999) <= -2.0 then -2.0
            else net_pnl
        end as pnl_take15_stop2,

        case
            when coalesce(max_high - entry_price, -999999) >= 2.0 then 2.0
            when coalesce(min_low - entry_price, 999999) <= -3.0 then -3.0
            else net_pnl
        end as pnl_take2_stop3,

        case
            when coalesce(max_high - entry_price, -999999) >= 2.0 then 2.0
            when coalesce(min_low - entry_price, 999999) <= -4.0 then -4.0
            else net_pnl
        end as pnl_take2_stop4,

        case
            when coalesce(max_high - entry_price, -999999) >= 3.0 then 3.0
            when coalesce(min_low - entry_price, 999999) <= -4.0 then -4.0
            else net_pnl
        end as pnl_take3_stop4,

        case
            when coalesce(max_high - entry_price, -999999) >= 3.0 then 3.0
            when coalesce(min_low - entry_price, 999999) <= -5.0 then -5.0
            else net_pnl
        end as pnl_take3_stop5

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
        "mfe_oracle_reference_only": [],
        "take1_5_stop2": [],
        "take2_stop3": [],
        "take2_stop4": [],
        "take3_stop4": [],
        "take3_stop5": [],
    }

    for row in rows:
        (
            trade_id,
            net_pnl,
            entry_price,
            pnl_2h,
            pnl_4h,
            pnl_8h,
            pnl_session,
            pnl_mfe,
            pnl_take15_stop2,
            pnl_take2_stop3,
            pnl_take2_stop4,
            pnl_take3_stop4,
            pnl_take3_stop5,
        ) = row

        policies["historical_time_exit"].append(float(net_pnl or 0))
        policies["time_stop_2h"].append(float(pnl_2h or 0))
        policies["time_stop_4h"].append(float(pnl_4h or 0))
        policies["time_stop_8h"].append(float(pnl_8h or 0))
        policies["end_of_session"].append(float(pnl_session or 0))
        policies["mfe_oracle_reference_only"].append(float(pnl_mfe or 0))
        policies["take1_5_stop2"].append(float(pnl_take15_stop2 or 0))
        policies["take2_stop3"].append(float(pnl_take2_stop3 or 0))
        policies["take2_stop4"].append(float(pnl_take2_stop4 or 0))
        policies["take3_stop4"].append(float(pnl_take3_stop4 or 0))
        policies["take3_stop5"].append(float(pnl_take3_stop5 or 0))

    results = [metrics(policy, values) for policy, values in policies.items()]

    print("CANDIDATE_POLICIES")
    for i, row in enumerate(results, start=1):
        print_row("POLICY_ROW", i, row)

    ranked = sorted(
        results,
        key=lambda r: (
            int(r["passed"]),
            r["score"],
            r["net_pnl"],
        ),
        reverse=True,
    )

    print()
    print("RANKING")
    for i, row in enumerate(ranked, start=1):
        print_row("RANK_ROW", i, row)

    winner = ranked[0]
    pf = winner["profit_factor"]
    print()
    print(
        f"WINNER_POLICY={winner['policy']} "
        f"WINNER_NET_PNL={winner['net_pnl']:.8f} "
        f"WINNER_EXPECTANCY={winner['expectancy']:.8f} "
        f"WINNER_PF={'None' if pf is None else f'{pf:.8f}'} "
        f"WINNER_SCORE={winner['score']:.8f} "
        f"WINNER_PASSED={int(winner['passed'])}"
    )

    accepted = [r for r in ranked if r["passed"]]
    print(f"ACCEPTED_CANDIDATES={len(accepted)}")

    if accepted:
        print("VERDICT=EXIT_POLICY_CANDIDATE_FOUND")
    else:
        print("VERDICT=NO_POLICY_PASSED")


if __name__ == "__main__":
    main()
