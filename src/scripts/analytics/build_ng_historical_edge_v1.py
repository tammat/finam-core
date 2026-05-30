from __future__ import annotations

import argparse
import subprocess

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url


DEFAULT_SYMBOLS = [
    "NGF6@RTSX",
    "NGG6@RTSX",
    "NGH6@RTSX",
    "NGJ6@RTSX",
    "NGK6@RTSX",
    "NGM6@RTSX",
    "NGN6@RTSX",
    "NGQ6@RTSX",
]


EDGE_SQL = """
with bars as (
    select
        symbol,
        ts,
        close,
        high,
        low,
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
        ) as future_close
    from market_bars
    where timeframe = %(timeframe)s
      and symbol = any(%(symbols)s)
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
        end as side
    from bars
),
outcomes as (
    select
        symbol,
        side,
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
)
select
    symbol,
    side,
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
from outcomes
group by symbol, side
order by symbol, side;
"""


EDGE_TOTAL_SQL = """
with bars as (
    select
        symbol,
        ts,
        close,
        high,
        low,
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
        ) as future_close
    from market_bars
    where timeframe = %(timeframe)s
      and symbol = any(%(symbols)s)
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
        end as side
    from bars
),
outcomes as (
    select
        side,
        case
            when side = 'BUY' then future_close - entry_close
            when side = 'SELL' then entry_close - future_close
            else null
        end as pnl_points
    from signals
    where side is not null
      and future_close is not null
)
select
    side,
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
from outcomes
group by side
order by side;
"""


def git_clean() -> bool:
    result = subprocess.run(
        ["git", "status", "--short"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() == ""


def parse_symbols(value: str | None) -> list[str]:
    if not value:
        return DEFAULT_SYMBOLS
    return [item.strip() for item in value.split(",") if item.strip()]


def sample_quality(trades: int) -> str:
    if trades < 50:
        return "LOW"
    if trades < 150:
        return "MEDIUM"
    if trades < 300:
        return "HIGH"
    return "VERY_HIGH"


def fmt(value) -> str:
    if value is None:
        return "нет_данных"
    return f"{float(value):.6f}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", default="")
    parser.add_argument("--timeframe", default="M5")
    parser.add_argument("--lookback", type=int, default=20)
    parser.add_argument("--horizons", default="3,6,12,24")
    args = parser.parse_args()

    symbols = parse_symbols(args.symbols)
    horizons = [int(x.strip()) for x in args.horizons.split(",") if x.strip()]

    print("NG_HISTORICAL_EDGE_V1", flush=True)
    print(
        "NG_EDGE_CONFIG",
        f"git_clean={git_clean()}",
        f"timeframe={args.timeframe}",
        f"lookback={args.lookback}",
        f"horizons={','.join(map(str, horizons))}",
        f"symbols={','.join(symbols)}",
        flush=True,
    )

    with psycopg.connect(build_psycopg_url(), row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            for horizon in horizons:
                params = {
                    "symbols": symbols,
                    "timeframe": args.timeframe,
                    "lookback": args.lookback,
                    "horizon": horizon,
                }

                cur.execute(EDGE_TOTAL_SQL, params)
                total_rows = [dict(row) for row in cur.fetchall()]

                cur.execute(EDGE_SQL, params)
                symbol_rows = [dict(row) for row in cur.fetchall()]

                for row in total_rows:
                    print(
                        "NG_EDGE_TOTAL",
                        f"horizon_bars={horizon}",
                        f"side={row.get('side')}",
                        f"trades={row.get('trades')}",
                        f"sample_quality={sample_quality(int(row.get('trades') or 0))}",
                        f"wins={row.get('wins')}",
                        f"losses={row.get('losses')}",
                        f"winrate={row.get('winrate')}",
                        f"expectancy_points={row.get('expectancy_points')}",
                        f"total_pnl_points={row.get('total_pnl_points')}",
                        f"profit_factor={row.get('profit_factor')}",
                        flush=True,
                    )

                for row in symbol_rows:
                    print(
                        "NG_EDGE_SYMBOL",
                        f"horizon_bars={horizon}",
                        f"symbol={row.get('symbol')}",
                        f"side={row.get('side')}",
                        f"trades={row.get('trades')}",
                        f"sample_quality={sample_quality(int(row.get('trades') or 0))}",
                        f"wins={row.get('wins')}",
                        f"losses={row.get('losses')}",
                        f"winrate={row.get('winrate')}",
                        f"expectancy_points={row.get('expectancy_points')}",
                        f"total_pnl_points={row.get('total_pnl_points')}",
                        f"avg_win_points={row.get('avg_win_points')}",
                        f"avg_loss_points={row.get('avg_loss_points')}",
                        f"profit_factor={row.get('profit_factor')}",
                        flush=True,
                    )

    print("NG_HISTORICAL_EDGE_V1_OK", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
