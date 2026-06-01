from __future__ import annotations

import argparse
import subprocess

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url


CANDIDATES = [
    # horizon, side, regime, volatility, session
    (6, "BUY", "trend", "normal", "moscow_morning"),
    (6, "BUY", "trend", "high", "evening"),
    (12, "BUY", "trend", "low", "moscow_midday"),
    (12, "BUY", "trend", "normal", "moscow_morning"),
    (24, "BUY", "trend", "low", "moscow_midday"),
    (24, "BUY", "trend", "normal", "evening"),
    (24, "BUY", "range", "normal", "evening"),
]


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
        ts,
        side,
        regime,
        volatility,
        session,
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
    round(
        (
            sum(pnl_points) filter (where pnl_points > 0)
            / nullif(abs(sum(pnl_points) filter (where pnl_points < 0)), 0)
        )::numeric,
        6
    ) as profit_factor
from bucketed
where bucket in ('TRAIN', 'TEST')
group by bucket;
"""


def git_clean() -> bool:
    result = subprocess.run(["git", "status", "--short"], capture_output=True, text=True)
    return result.stdout.strip() == ""


def f(value) -> float:
    return 0.0 if value is None else float(value)


def decision(test_trades: int, test_exp: float, test_pf: float) -> str:
    if test_trades >= 30 and test_exp > 0 and test_pf >= 1.10:
        return "OOS_PASS"
    if test_trades >= 10 and test_exp > 0 and test_pf >= 1.00:
        return "OOS_WATCH"
    if test_trades < 10:
        return "OOS_INSUFFICIENT_SAMPLE"
    return "OOS_FAIL"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="BRM6@RTSX")
    parser.add_argument("--timeframe", default="M5")
    parser.add_argument("--lookback", type=int, default=20)
    parser.add_argument("--horizons", default="6,12,24")
    parser.add_argument("--train-from", default="2026-04-01")
    parser.add_argument("--train-to", default="2026-05-19")
    parser.add_argument("--test-from", default="2026-05-20")
    parser.add_argument("--test-to", default="")
    args = parser.parse_args()

    allowed_horizons = {int(x.strip()) for x in args.horizons.split(",") if x.strip()}
    candidates = [c for c in CANDIDATES if c[0] in allowed_horizons]

    print("BR_CANDIDATES_OOS_VALIDATION_V2", flush=True)
    print(
        "BR_CANDIDATES_OOS_CONFIG",
        f"git_clean={git_clean()}",
        f"symbol={args.symbol}",
        f"timeframe={args.timeframe}",
        f"lookback={args.lookback}",
        f"horizons={','.join(map(str, sorted(allowed_horizons)))}",
        f"train_from={args.train_from}",
        f"train_to={args.train_to}",
        f"test_from={args.test_from}",
        f"test_to={args.test_to or 'NOW'}",
        f"candidates={len(candidates)}",
        flush=True,
    )

    passed = 0
    watched = 0
    failed = 0
    insufficient = 0

    with psycopg.connect(build_psycopg_url(), row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            for horizon, side, regime, volatility, session in candidates:
                params = {
                    "symbol": args.symbol,
                    "timeframe": args.timeframe,
                    "lookback": args.lookback,
                    "horizon": horizon,
                    "side": side,
                    "regime": regime,
                    "volatility": volatility,
                    "session": session,
                    "train_from": args.train_from,
                    "train_to": args.train_to,
                    "test_from": args.test_from,
                    "test_to": args.test_to,
                }

                cur.execute(SQL, params)
                rows = {row["bucket"]: dict(row) for row in cur.fetchall()}

                train = rows.get("TRAIN", {})
                test = rows.get("TEST", {})

                test_trades = int(test.get("trades") or 0)
                test_exp = f(test.get("expectancy_points"))
                test_pf = f(test.get("profit_factor"))
                d = decision(test_trades, test_exp, test_pf)

                if d == "OOS_PASS":
                    passed += 1
                elif d == "OOS_WATCH":
                    watched += 1
                elif d == "OOS_INSUFFICIENT_SAMPLE":
                    insufficient += 1
                else:
                    failed += 1

                print(
                    "BR_CANDIDATES_OOS_ROW",
                    f"candidate={side}:{regime}:{volatility}:{session}:h{horizon}",
                    f"train_trades={int(train.get('trades') or 0)}",
                    f"train_exp={train.get('expectancy_points', 'нет_данных')}",
                    f"train_pf={train.get('profit_factor', 'нет_данных')}",
                    f"test_trades={test_trades}",
                    f"test_wins={test.get('wins', 0)}",
                    f"test_losses={test.get('losses', 0)}",
                    f"test_winrate={test.get('winrate', 'нет_данных')}",
                    f"test_exp={test.get('expectancy_points', 'нет_данных')}",
                    f"test_pnl={test.get('total_pnl_points', 'нет_данных')}",
                    f"test_pf={test.get('profit_factor', 'нет_данных')}",
                    f"decision={d}",
                    flush=True,
                )

    print(
        "BR_CANDIDATES_OOS_FINAL",
        f"passed={passed}",
        f"watch={watched}",
        f"insufficient={insufficient}",
        f"failed={failed}",
        flush=True,
    )

    print("BR_CANDIDATES_OOS_VALIDATION_V2_OK", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
