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


BARS_SQL = """
select
    symbol,
    timeframe,
    count(*)::int as bars,
    min(ts) as first_bar,
    max(ts) as last_bar,
    round(avg(close)::numeric, 6) as avg_close,
    round(min(close)::numeric, 6) as min_close,
    round(max(close)::numeric, 6) as max_close
from market_bars
where timeframe = %(timeframe)s
  and symbol = any(%(symbols)s)
group by symbol, timeframe
order by symbol, timeframe;
"""


BAR_RETURNS_SQL = """
with ordered as (
    select
        symbol,
        ts,
        close,
        lag(close) over (partition by symbol order by ts) as prev_close
    from market_bars
    where timeframe = %(timeframe)s
      and symbol = any(%(symbols)s)
),
returns as (
    select
        symbol,
        ts,
        close,
        prev_close,
        close - prev_close as ret_points,
        case
            when prev_close is not null and prev_close <> 0
            then (close - prev_close) / prev_close
            else null
        end as ret_pct
    from ordered
    where prev_close is not null
)
select
    symbol,
    count(*)::int as returns,
    round(avg(ret_points)::numeric, 8) as avg_ret_points,
    round(avg(abs(ret_points))::numeric, 8) as avg_abs_ret_points,
    round(stddev_samp(ret_points)::numeric, 8) as std_ret_points,
    round(min(ret_points)::numeric, 8) as min_ret_points,
    round(max(ret_points)::numeric, 8) as max_ret_points
from returns
group by symbol
order by symbol;
"""


BREAKOUT_SQL = """
with ordered as (
    select
        symbol,
        ts,
        close,
        max(high) over (
            partition by symbol
            order by ts
            rows between %(lookback)s preceding and 1 preceding
        ) as prev_high,
        min(low) over (
            partition by symbol
            order by ts
            rows between %(lookback)s preceding and 1 preceding
        ) as prev_low
    from market_bars
    where timeframe = %(timeframe)s
      and symbol = any(%(symbols)s)
),
signals as (
    select
        symbol,
        ts,
        close,
        case
            when prev_high is not null and close > prev_high then 'BUY'
            when prev_low is not null and close < prev_low then 'SELL'
            else null
        end as side
    from ordered
)
select
    symbol,
    side,
    count(*)::int as signals
from signals
where side is not null
group by symbol, side
order by symbol, side;
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", default="")
    parser.add_argument("--timeframe", default="M5")
    parser.add_argument("--lookback", type=int, default=20)
    args = parser.parse_args()

    symbols = parse_symbols(args.symbols)

    params = {
        "symbols": symbols,
        "timeframe": args.timeframe,
        "lookback": args.lookback,
    }

    with psycopg.connect(build_psycopg_url(), row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(BARS_SQL, params)
            bar_rows = [dict(row) for row in cur.fetchall()]

            cur.execute(BAR_RETURNS_SQL, params)
            return_rows = [dict(row) for row in cur.fetchall()]

            cur.execute(BREAKOUT_SQL, params)
            signal_rows = [dict(row) for row in cur.fetchall()]

    total_bars = sum(int(row.get("bars") or 0) for row in bar_rows)
    total_signals = sum(int(row.get("signals") or 0) for row in signal_rows)

    print("NG_HISTORICAL_REPLAY_RESEARCH_V1", flush=True)
    print(
        "NG_RESEARCH_SUMMARY",
        f"git_clean={git_clean()}",
        f"timeframe={args.timeframe}",
        f"lookback={args.lookback}",
        f"symbols={','.join(symbols)}",
        f"symbols_count={len(symbols)}",
        f"total_bars={total_bars}",
        f"total_breakout_signals={total_signals}",
        flush=True,
    )

    for row in bar_rows:
        print(
            "NG_RESEARCH_BARS",
            f"symbol={row.get('symbol')}",
            f"timeframe={row.get('timeframe')}",
            f"bars={row.get('bars')}",
            f"first_bar={row.get('first_bar')}",
            f"last_bar={row.get('last_bar')}",
            f"avg_close={row.get('avg_close')}",
            f"min_close={row.get('min_close')}",
            f"max_close={row.get('max_close')}",
            flush=True,
        )

    for row in return_rows:
        print(
            "NG_RESEARCH_RETURNS",
            f"symbol={row.get('symbol')}",
            f"returns={row.get('returns')}",
            f"avg_ret_points={row.get('avg_ret_points')}",
            f"avg_abs_ret_points={row.get('avg_abs_ret_points')}",
            f"std_ret_points={row.get('std_ret_points')}",
            f"min_ret_points={row.get('min_ret_points')}",
            f"max_ret_points={row.get('max_ret_points')}",
            flush=True,
        )

    for row in signal_rows:
        print(
            "NG_RESEARCH_BREAKOUT_SIGNALS",
            f"symbol={row.get('symbol')}",
            f"side={row.get('side')}",
            f"signals={row.get('signals')}",
            flush=True,
        )

    print("NG_HISTORICAL_REPLAY_RESEARCH_V1_OK", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
