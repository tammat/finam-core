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
filtered as (
    select *
    from outcomes
    where side = %(side)s
      and regime = %(regime)s
      and volatility = %(volatility)s
      and session = %(session)s
)
select
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
from filtered;
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

    args = parser.parse_args()

    print("BR_CANDIDATE_REPLAY_FILTER_V1", flush=True)
    print(
        "BR_CANDIDATE_REPLAY_CONFIG",
        f"git_clean={git_clean()}",
        f"symbol={args.symbol}",
        f"timeframe={args.timeframe}",
        f"lookback={args.lookback}",
        f"horizon={args.horizon}",
        f"side={args.side}",
        f"regime={args.regime}",
        f"volatility={args.volatility}",
        f"session={args.session}",
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
    }

    with psycopg.connect(build_psycopg_url(), row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(SQL, params)
            row = dict(cur.fetchone())

    trades = int(row.get("trades") or 0)
    pf = float(row.get("profit_factor") or 0)
    expectancy = float(row.get("expectancy_points") or 0)

    decision = "PASS_TO_PAPER_VALIDATION" if trades >= 100 and expectancy > 0 and pf >= 1.15 else "REJECT_OR_WATCH"

    print(
        "BR_CANDIDATE_REPLAY_ROW",
        f"trades={trades}",
        f"wins={row.get('wins')}",
        f"losses={row.get('losses')}",
        f"winrate={row.get('winrate')}",
        f"expectancy_points={row.get('expectancy_points')}",
        f"total_pnl_points={row.get('total_pnl_points')}",
        f"avg_win_points={fmt(row.get('avg_win_points'))}",
        f"avg_loss_points={fmt(row.get('avg_loss_points'))}",
        f"profit_factor={fmt(row.get('profit_factor'))}",
        f"decision={decision}",
        flush=True,
    )

    print(
        "BR_CANDIDATE_REPLAY_SUMMARY",
        f"candidate={args.side}:{args.regime}:{args.volatility}:{args.session}:h{args.horizon}",
        f"decision={decision}",
        flush=True,
    )

    print("BR_CANDIDATE_REPLAY_FILTER_V1_OK", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
