from __future__ import annotations

import argparse
import subprocess

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url


SQL = """
with bars as (
    select
        symbol,
        ts,
        close,
        high,
        low,
        extract(hour from ts at time zone 'Europe/Moscow')::int as hour_msk,

        max(high) over (
            partition by symbol
            order by ts
            rows between %(lookback)s preceding and 1 preceding
        ) as prev_high,

        min(low) over (
            partition by symbol
            order by ts
            rows between %(lookback)s preceding and 1 preceding
        ) as prev_low,

        lead(close, %(horizon)s) over (
            partition by symbol
            order by ts
        ) as future_close,

        avg(close) over (
            partition by symbol
            order by ts
            rows between 20 preceding and 1 preceding
        ) as ma20,

        avg(close) over (
            partition by symbol
            order by ts
            rows between 60 preceding and 1 preceding
        ) as ma60,

        avg(high - low) over (
            partition by symbol
            order by ts
            rows between 20 preceding and 1 preceding
        ) as atr20,

        avg(high - low) over (
            partition by symbol
            order by ts
            rows between 100 preceding and 1 preceding
        ) as atr100

    from market_bars
    where timeframe = %(timeframe)s
      and symbol = %(symbol)s
),
signals as (
    select
        symbol,
        ts,
        close as entry_close,
        future_close,

        case
            when prev_high is not null and close > prev_high then 'BUY'
            when prev_low is not null and close < prev_low then 'SELL'
            else null
        end as side,

        case
            when ma20 is null or ma60 is null then 'unknown'
            when abs(ma20 - ma60) / nullif(close, 0) >= 0.0015 then 'trend'
            else 'range'
        end as regime,

        case
            when atr20 is null or atr100 is null then 'unknown'
            when atr20 < atr100 * 0.75 then 'low'
            when atr20 > atr100 * 1.25 then 'high'
            else 'normal'
        end as volatility,

        case
            when hour_msk between 3 and 8 then 'asia'
            when hour_msk between 9 and 11 then 'moscow_morning'
            when hour_msk between 12 and 16 then 'moscow_midday'
            when hour_msk between 17 and 23 then 'evening'
            else 'night'
        end as session

    from bars
),
outcomes as (
    select
        symbol,
        ts,
        side,
        regime,
        volatility,
        session,
        entry_close,
        future_close,
        case
            when side = 'BUY' then future_close - entry_close
            when side = 'SELL' then entry_close - future_close
            else null
        end as pnl_points
    from signals
    where side is not null
      and future_close is not null
),
candidate as (
    select *
    from outcomes
    where side = %(side)s
      and regime = %(regime)s
      and volatility = %(volatility)s
      and session = %(session)s
),
bucketed as (
    select
        case
            when ts >= %(train_from)s::timestamptz
             and ts <  %(train_to)s::timestamptz then 'TRAIN'
            when ts >= %(test_from)s::timestamptz
             and (%(test_to)s::text = '' or ts < %(test_to)s::timestamptz) then 'TEST'
            else 'OUTSIDE'
        end as bucket,
        pnl_points
    from candidate
)
select
    bucket,
    count(*)::int as trades,
    count(*) filter (where pnl_points > 0)::int as wins,
    count(*) filter (where pnl_points < 0)::int as losses,
    round(avg(pnl_points)::numeric, 6) as expectancy_points,
    round(sum(pnl_points)::numeric, 6) as total_pnl_points,
    round(
        (
            count(*) filter (where pnl_points > 0)::numeric
            / nullif(count(*), 0)
        ),
        6
    ) as winrate,
    round(avg(pnl_points) filter (where pnl_points > 0)::numeric, 6) as avg_win_points,
    round(avg(abs(pnl_points)) filter (where pnl_points < 0)::numeric, 6) as avg_loss_points,
    round(
        (
            sum(pnl_points) filter (where pnl_points > 0)
            / nullif(abs(sum(pnl_points) filter (where pnl_points < 0)), 0)
        )::numeric,
        6
    ) as profit_factor
from bucketed
where bucket in ('TRAIN', 'TEST')
group by bucket
order by bucket;
"""


def git_clean() -> bool:
    result = subprocess.run(
        ["git", "status", "--short"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() == ""


def fmt(value) -> str:
    if value is None:
        return "нет_данных"
    return f"{float(value):.6f}"


def decision(trades: int, expectancy: float, pf: float) -> str:
    if trades >= 30 and expectancy > 0 and pf >= 1.10:
        return "OUT_OF_SAMPLE_PASS"
    if trades >= 10 and expectancy > 0 and pf >= 1.00:
        return "OUT_OF_SAMPLE_WATCH"
    return "OUT_OF_SAMPLE_FAIL"


def f(value) -> float:
    if value is None:
        return 0.0
    return float(value)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="BRM6@RTSX")
    parser.add_argument("--timeframe", default="M5")
    parser.add_argument("--lookback", type=int, default=20)
    parser.add_argument("--horizon", type=int, default=24)

    parser.add_argument("--side", default="BUY")
    parser.add_argument("--regime", default="trend")
    parser.add_argument("--volatility", default="normal")
    parser.add_argument("--session", default="evening")

    parser.add_argument("--train-from", default="2026-04-01")
    parser.add_argument("--train-to", default="2026-05-19")
    parser.add_argument("--test-from", default="2026-05-20")
    parser.add_argument("--test-to", default="")

    args = parser.parse_args()

    print("BR_CANDIDATE_OOS_VALIDATION_V1", flush=True)
    print(
        "BR_CANDIDATE_OOS_CONFIG",
        f"git_clean={git_clean()}",
        f"symbol={args.symbol}",
        f"timeframe={args.timeframe}",
        f"lookback={args.lookback}",
        f"horizon={args.horizon}",
        f"candidate={args.side}:{args.regime}:{args.volatility}:{args.session}:h{args.horizon}",
        f"train_from={args.train_from}",
        f"train_to={args.train_to}",
        f"test_from={args.test_from}",
        f"test_to={args.test_to or 'NOW'}",
        flush=True,
    )

    params = {
        "symbol": args.symbol,
        "timeframe": args.timeframe,
        "lookback": args.lookback,
        "horizon": args.horizon,
        "side": args.side,
        "regime": args.regime,
        "volatility": args.volatility,
        "session": args.session,
        "train_from": args.train_from,
        "train_to": args.train_to,
        "test_from": args.test_from,
        "test_to": args.test_to,
    }

    with psycopg.connect(build_psycopg_url(), row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(SQL, params)
            rows = {row["bucket"]: dict(row) for row in cur.fetchall()}

    train = rows.get("TRAIN", {})
    test = rows.get("TEST", {})

    for name, row in (("TRAIN", train), ("TEST", test)):
        trades = int(row.get("trades") or 0)
        expectancy = f(row.get("expectancy_points"))
        pf = f(row.get("profit_factor"))
        d = decision(trades, expectancy, pf) if name == "TEST" else "REFERENCE"

        print(
            "BR_CANDIDATE_OOS_ROW",
            f"bucket={name}",
            f"trades={trades}",
            f"wins={row.get('wins', 0)}",
            f"losses={row.get('losses', 0)}",
            f"winrate={row.get('winrate', 'нет_данных')}",
            f"expectancy_points={row.get('expectancy_points', 'нет_данных')}",
            f"total_pnl_points={row.get('total_pnl_points', 'нет_данных')}",
            f"avg_win_points={fmt(row.get('avg_win_points'))}",
            f"avg_loss_points={fmt(row.get('avg_loss_points'))}",
            f"profit_factor={fmt(row.get('profit_factor'))}",
            f"decision={d}",
            flush=True,
        )

    train_exp = f(train.get("expectancy_points"))
    test_exp = f(test.get("expectancy_points"))
    train_pf = f(train.get("profit_factor"))
    test_pf = f(test.get("profit_factor"))

    exp_delta = test_exp - train_exp
    pf_delta = test_pf - train_pf

    final_decision = decision(
        int(test.get("trades") or 0),
        test_exp,
        test_pf,
    )

    print(
        "BR_CANDIDATE_OOS_COMPARISON",
        f"expectancy_delta={exp_delta:.6f}",
        f"profit_factor_delta={pf_delta:.6f}",
        flush=True,
    )

    print(
        "BR_CANDIDATE_OOS_FINAL",
        f"decision={final_decision}",
        "next_step=LIVE_PAPER_ACCUMULATION" if final_decision == "OUT_OF_SAMPLE_PASS" else "next_step=REJECT_OR_RETEST_OTHER_CANDIDATE",
        flush=True,
    )

    print("BR_CANDIDATE_OOS_VALIDATION_V1_OK", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
