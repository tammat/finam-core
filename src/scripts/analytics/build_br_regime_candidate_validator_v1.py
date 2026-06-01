from __future__ import annotations

import argparse
import subprocess

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url


DEFAULT_SYMBOLS = ["BRM6@RTSX"]


CANDIDATE_SQL = """
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
combo_stats as (
    select
        symbol,
        side,
        regime,
        volatility,
        session,
        count(*)::int as trades,
        count(*) filter (where pnl_points > 0)::int as wins,
        count(*) filter (where pnl_points < 0)::int as losses,
        avg(pnl_points) as expectancy_raw,
        sum(pnl_points) as total_pnl_raw,
        (
            count(*) filter (where pnl_points > 0)::numeric
            / nullif(count(*), 0)
        ) as winrate_raw,
        avg(pnl_points) filter (where pnl_points > 0) as avg_win_raw,
        avg(abs(pnl_points)) filter (where pnl_points < 0) as avg_loss_raw,
        (
            sum(pnl_points) filter (where pnl_points > 0)
            / nullif(abs(sum(pnl_points) filter (where pnl_points < 0)), 0)
        ) as profit_factor_raw
    from outcomes
    group by symbol, side, regime, volatility, session
)
select
    symbol,
    side,
    regime,
    volatility,
    session,
    trades,
    wins,
    losses,
    round(expectancy_raw::numeric, 6) as expectancy_points,
    round(total_pnl_raw::numeric, 6) as total_pnl_points,
    round(winrate_raw::numeric, 6) as winrate,
    round(avg_win_raw::numeric, 6) as avg_win_points,
    round(avg_loss_raw::numeric, 6) as avg_loss_points,
    round(profit_factor_raw::numeric, 6) as profit_factor,
    round((expectancy_raw * trades)::numeric, 6) as edge_score,
    round((expectancy_raw * trades * coalesce(profit_factor_raw, 0))::numeric, 6) as quality_score
from combo_stats
where trades >= %(min_trades)s
  and expectancy_raw > 0
  and profit_factor_raw >= %(min_profit_factor)s
order by quality_score desc, edge_score desc, trades desc;
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


def strength(trades: int, pf: float, expectancy: float) -> str:
    if trades >= 100 and pf >= 1.20 and expectancy > 0:
        return "STRONG"
    if trades >= 50 and pf >= 1.10 and expectancy > 0:
        return "MEDIUM"
    return "WEAK"


def fmt(value) -> str:
    if value is None:
        return "нет_данных"
    return f"{float(value):.6f}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="")
    parser.add_argument("--symbols", default="")
    parser.add_argument("--timeframe", default="M5")
    parser.add_argument("--lookback", type=int, default=20)
    parser.add_argument("--horizons", default="3,6,12,24")
    parser.add_argument("--min-trades", type=int, default=50)
    parser.add_argument("--min-profit-factor", type=float, default=1.10)
    args = parser.parse_args()

    symbols = parse_symbols(args.symbols or args.symbol)
    horizons = [int(x.strip()) for x in args.horizons.split(",") if x.strip()]

    print("BR_REGIME_CANDIDATE_VALIDATOR_V1", flush=True)
    print(
        "BR_REGIME_CANDIDATE_CONFIG",
        f"git_clean={git_clean()}",
        f"timeframe={args.timeframe}",
        f"lookback={args.lookback}",
        f"horizons={','.join(map(str, horizons))}",
        f"symbols={','.join(symbols)}",
        f"min_trades={args.min_trades}",
        f"min_profit_factor={args.min_profit_factor}",
        "scope=combo_only",
        "excluded=single_factor_rules",
        flush=True,
    )

    total_candidates = 0

    with psycopg.connect(build_psycopg_url(), row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            for horizon in horizons:
                params = {
                    "symbols": symbols,
                    "timeframe": args.timeframe,
                    "lookback": args.lookback,
                    "horizon": horizon,
                    "min_trades": args.min_trades,
                    "min_profit_factor": args.min_profit_factor,
                }

                cur.execute(CANDIDATE_SQL, params)
                rows = [dict(row) for row in cur.fetchall()]
                total_candidates += len(rows)

                for rank, row in enumerate(rows, start=1):
                    trades = int(row.get("trades") or 0)
                    pf = float(row.get("profit_factor") or 0)
                    expectancy = float(row.get("expectancy_points") or 0)

                    print(
                        "BR_REGIME_CANDIDATE_ROW",
                        f"horizon_bars={horizon}",
                        f"rank={rank}",
                        f"symbol={row.get('symbol')}",
                        f"side={row.get('side')}",
                        f"regime={row.get('regime')}",
                        f"volatility={row.get('volatility')}",
                        f"session={row.get('session')}",
                        f"trades={trades}",
                        f"wins={row.get('wins')}",
                        f"losses={row.get('losses')}",
                        f"winrate={row.get('winrate')}",
                        f"expectancy_points={row.get('expectancy_points')}",
                        f"total_pnl_points={row.get('total_pnl_points')}",
                        f"avg_win_points={fmt(row.get('avg_win_points'))}",
                        f"avg_loss_points={fmt(row.get('avg_loss_points'))}",
                        f"profit_factor={fmt(row.get('profit_factor'))}",
                        f"edge_score={fmt(row.get('edge_score'))}",
                        f"quality_score={fmt(row.get('quality_score'))}",
                        f"strength={strength(trades, pf, expectancy)}",
                        "decision=VALIDATE_IN_REPLAY_OR_PAPER",
                        flush=True,
                    )

                print(
                    "BR_REGIME_CANDIDATE_SUMMARY",
                    f"horizon_bars={horizon}",
                    f"candidates={len(rows)}",
                    flush=True,
                )

    print(
        "BR_REGIME_CANDIDATE_FINAL",
        f"total_candidates={total_candidates}",
        "single_factor_rules=REJECTED_AS_INSUFFICIENT",
        flush=True,
    )
    print("BR_REGIME_CANDIDATE_VALIDATOR_V1_OK", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
