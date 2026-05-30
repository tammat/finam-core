from __future__ import annotations

import argparse
import subprocess

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url


DEFAULT_SYMBOLS = [
    "USDRUBF@RTSX",
]


REPLAY_SQL = """
with bars as (
    select
        symbol,
        ts,
        close,
        high,
        low,
        extract(hour from ts + interval '3 hours')::int as hour_msk,
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
        hour_msk,
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
        ts,
        hour_msk,
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
),
profile as (
    select
        symbol,
        side,
        hour_msk,
        count(*)::int as profile_trades,
        avg(pnl_points)::float as profile_expectancy
    from outcomes
    group by symbol, side, hour_msk
),
joined as (
    select
        o.*,
        p.profile_trades,
        p.profile_expectancy,
        case
            when p.profile_trades >= %(min_profile_trades)s
             and p.profile_expectancy > %(min_expectancy)s
            then true
            else false
        end as governance_allowed
    from outcomes o
    join profile p
      on p.symbol = o.symbol
     and p.side = o.side
     and p.hour_msk = o.hour_msk
)
select
    symbol,
    side,
    count(*)::int as baseline_rows,
    count(*) filter (where governance_allowed is true)::int as governance_rows,
    count(*) filter (where governance_allowed is false)::int as blocked_rows,
    avg(pnl_points)::float as baseline_expectancy,
    avg(pnl_points) filter (where governance_allowed is true)::float as governance_expectancy,
    sum(pnl_points)::float as baseline_pnl_points,
    sum(pnl_points) filter (where governance_allowed is true)::float as governance_pnl_points,
    coalesce(sum(case when governance_allowed is false and pnl_points < 0 then abs(pnl_points) else 0 end), 0)::float as saved_loss_points,
    coalesce(sum(case when governance_allowed is false and pnl_points > 0 then pnl_points else 0 end), 0)::float as missed_profit_points
from joined
group by symbol, side
order by symbol, side;
"""


REPLAY_TOTAL_SQL = """
with bars as (
    select
        symbol,
        ts,
        close,
        high,
        low,
        extract(hour from ts + interval '3 hours')::int as hour_msk,
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
        hour_msk,
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
        ts,
        hour_msk,
        side,
        case
            when side = 'BUY' then future_close - entry_close
            when side = 'SELL' then entry_close - future_close
            else null
        end as pnl_points
    from signals
    where side is not null
      and future_close is not null
),
profile as (
    select
        symbol,
        side,
        hour_msk,
        count(*)::int as profile_trades,
        avg(pnl_points)::float as profile_expectancy
    from outcomes
    group by symbol, side, hour_msk
),
joined as (
    select
        o.*,
        p.profile_trades,
        p.profile_expectancy,
        case
            when p.profile_trades >= %(min_profile_trades)s
             and p.profile_expectancy > %(min_expectancy)s
            then true
            else false
        end as governance_allowed
    from outcomes o
    join profile p
      on p.symbol = o.symbol
     and p.side = o.side
     and p.hour_msk = o.hour_msk
)
select
    side,
    count(*)::int as baseline_rows,
    count(*) filter (where governance_allowed is true)::int as governance_rows,
    count(*) filter (where governance_allowed is false)::int as blocked_rows,
    avg(pnl_points)::float as baseline_expectancy,
    avg(pnl_points) filter (where governance_allowed is true)::float as governance_expectancy,
    sum(pnl_points)::float as baseline_pnl_points,
    sum(pnl_points) filter (where governance_allowed is true)::float as governance_pnl_points,
    coalesce(sum(case when governance_allowed is false and pnl_points < 0 then abs(pnl_points) else 0 end), 0)::float as saved_loss_points,
    coalesce(sum(case when governance_allowed is false and pnl_points > 0 then pnl_points else 0 end), 0)::float as missed_profit_points
from joined
group by side
order by side;
"""


PROFILE_SQL = """
with bars as (
    select
        symbol,
        ts,
        close,
        high,
        low,
        extract(hour from ts + interval '3 hours')::int as hour_msk,
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
        extract(hour from ts + interval '3 hours')::int as hour_msk,
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
        hour_msk,
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
    hour_msk,
    count(*)::int as trades,
    avg(pnl_points)::float as expectancy_points,
    sum(pnl_points)::float as total_pnl_points
from outcomes
group by symbol, side, hour_msk
having count(*) >= %(min_profile_trades)s
order by expectancy_points desc, trades desc
limit 30;
"""


def git_clean() -> bool:
    result = subprocess.run(["git", "status", "--short"], capture_output=True, text=True, check=False)
    return result.stdout.strip() == ""


def parse_symbols(value: str | None) -> list[str]:
    if not value:
        return DEFAULT_SYMBOLS
    return [item.strip() for item in value.split(",") if item.strip()]


def sample_quality(rows: int) -> str:
    if rows < 50:
        return "LOW"
    if rows < 150:
        return "MEDIUM"
    if rows < 300:
        return "HIGH"
    return "VERY_HIGH"


def fmt(value) -> str:
    if value is None:
        return "нет_данных"
    return f"{float(value):.6f}"


def alpha(saved_loss: float, missed_profit: float) -> float:
    return float(saved_loss or 0.0) - float(missed_profit or 0.0)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", default="")
    parser.add_argument("--timeframe", default="M5")
    parser.add_argument("--lookback", type=int, default=20)
    parser.add_argument("--horizon", type=int, default=24)
    parser.add_argument("--min-profile-trades", type=int, default=20)
    parser.add_argument("--min-expectancy", type=float, default=0.0)
    args = parser.parse_args()

    symbols = parse_symbols(args.symbols)

    params = {
        "symbols": symbols,
        "timeframe": args.timeframe,
        "lookback": args.lookback,
        "horizon": args.horizon,
        "min_profile_trades": args.min_profile_trades,
        "min_expectancy": args.min_expectancy,
    }

    with psycopg.connect(build_psycopg_url(), row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(REPLAY_TOTAL_SQL, params)
            total_rows = [dict(row) for row in cur.fetchall()]

            cur.execute(REPLAY_SQL, params)
            symbol_rows = [dict(row) for row in cur.fetchall()]

            cur.execute(PROFILE_SQL, params)
            profile_rows = [dict(row) for row in cur.fetchall()]

    print("USD_GOVERNANCE_REPLAY_V1", flush=True)
    print(
        "USD_GOVERNANCE_REPLAY_CONFIG",
        f"git_clean={git_clean()}",
        f"timeframe={args.timeframe}",
        f"lookback={args.lookback}",
        f"horizon_bars={args.horizon}",
        f"min_profile_trades={args.min_profile_trades}",
        f"min_expectancy={args.min_expectancy}",
        f"symbols={','.join(symbols)}",
        flush=True,
    )

    for row in total_rows:
        saved = float(row.get("saved_loss_points") or 0.0)
        missed = float(row.get("missed_profit_points") or 0.0)
        base = row.get("baseline_expectancy")
        gov = row.get("governance_expectancy")
        delta = float(gov) - float(base) if base is not None and gov is not None else None
        print(
            "USD_GOVERNANCE_REPLAY_TOTAL",
            f"side={row.get('side')}",
            f"baseline_rows={row.get('baseline_rows')}",
            f"governance_rows={row.get('governance_rows')}",
            f"blocked_rows={row.get('blocked_rows')}",
            f"sample_quality={sample_quality(int(row.get('baseline_rows') or 0))}",
            f"baseline_expectancy={fmt(base)}",
            f"governance_expectancy={fmt(gov)}",
            f"delta_expectancy={fmt(delta)}",
            f"baseline_pnl_points={fmt(row.get('baseline_pnl_points'))}",
            f"governance_pnl_points={fmt(row.get('governance_pnl_points'))}",
            f"saved_loss_points={saved:.6f}",
            f"missed_profit_points={missed:.6f}",
            f"governance_alpha_points={alpha(saved, missed):.6f}",
            flush=True,
        )

    for row in symbol_rows:
        saved = float(row.get("saved_loss_points") or 0.0)
        missed = float(row.get("missed_profit_points") or 0.0)
        base = row.get("baseline_expectancy")
        gov = row.get("governance_expectancy")
        delta = float(gov) - float(base) if base is not None and gov is not None else None
        print(
            "USD_GOVERNANCE_REPLAY_SYMBOL",
            f"symbol={row.get('symbol')}",
            f"side={row.get('side')}",
            f"baseline_rows={row.get('baseline_rows')}",
            f"governance_rows={row.get('governance_rows')}",
            f"blocked_rows={row.get('blocked_rows')}",
            f"sample_quality={sample_quality(int(row.get('baseline_rows') or 0))}",
            f"baseline_expectancy={fmt(base)}",
            f"governance_expectancy={fmt(gov)}",
            f"delta_expectancy={fmt(delta)}",
            f"baseline_pnl_points={fmt(row.get('baseline_pnl_points'))}",
            f"governance_pnl_points={fmt(row.get('governance_pnl_points'))}",
            f"saved_loss_points={saved:.6f}",
            f"missed_profit_points={missed:.6f}",
            f"governance_alpha_points={alpha(saved, missed):.6f}",
            flush=True,
        )

    for row in profile_rows:
        print(
            "USD_GOVERNANCE_PROFILE_TOP",
            f"symbol={row.get('symbol')}",
            f"side={row.get('side')}",
            f"hour_msk={row.get('hour_msk')}",
            f"trades={row.get('trades')}",
            f"expectancy_points={fmt(row.get('expectancy_points'))}",
            f"total_pnl_points={fmt(row.get('total_pnl_points'))}",
            flush=True,
        )

    print("USD_GOVERNANCE_REPLAY_V1_OK", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
