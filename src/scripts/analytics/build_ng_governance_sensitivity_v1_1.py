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


SENSITIVITY_SQL = """
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
        side,
        hour_msk,
        count(*)::int as profile_trades,
        avg(pnl_points)::float as profile_expectancy
    from outcomes
    group by side, hour_msk
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
      on p.side = o.side
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


def git_clean() -> bool:
    result = subprocess.run(["git", "status", "--short"], capture_output=True, text=True, check=False)
    return result.stdout.strip() == ""


def parse_symbols(value: str | None) -> list[str]:
    if not value:
        return DEFAULT_SYMBOLS
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_int_grid(value: str) -> list[int]:
    return [int(x.strip()) for x in value.split(",") if x.strip()]


def parse_float_grid(value: str) -> list[float]:
    return [float(x.strip()) for x in value.split(",") if x.strip()]


def fmt(value) -> str:
    if value is None:
        return "нет_данных"
    return f"{float(value):.6f}"


def quality(rows: int) -> str:
    if rows < 50:
        return "LOW"
    if rows < 150:
        return "MEDIUM"
    if rows < 300:
        return "HIGH"
    return "VERY_HIGH"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", default="")
    parser.add_argument("--timeframe", default="M5")
    parser.add_argument("--lookback", type=int, default=20)
    parser.add_argument("--horizon", type=int, default=24)
    parser.add_argument("--min-profile-trades-grid", default="5,10,15,20")
    parser.add_argument("--min-expectancy-grid", default="-0.005,0,0.005,0.01")
    args = parser.parse_args()

    symbols = parse_symbols(args.symbols)
    trades_grid = parse_int_grid(args.min_profile_trades_grid)
    expectancy_grid = parse_float_grid(args.min_expectancy_grid)

    print("NG_GOVERNANCE_SENSITIVITY_V1_1", flush=True)
    print(
        "NG_SENSITIVITY_CONFIG",
        "profile=NG_CONTINUOUS_SIDE_HOUR",
        f"git_clean={git_clean()}",
        f"timeframe={args.timeframe}",
        f"lookback={args.lookback}",
        f"horizon_bars={args.horizon}",
        f"min_profile_trades_grid={','.join(map(str, trades_grid))}",
        f"min_expectancy_grid={','.join(map(str, expectancy_grid))}",
        f"symbols={','.join(symbols)}",
        flush=True,
    )

    rows_all: list[dict] = []

    with psycopg.connect(build_psycopg_url(), row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            for min_profile_trades in trades_grid:
                for min_expectancy in expectancy_grid:
                    params = {
                        "symbols": symbols,
                        "timeframe": args.timeframe,
                        "lookback": args.lookback,
                        "horizon": args.horizon,
                        "min_profile_trades": min_profile_trades,
                        "min_expectancy": min_expectancy,
                    }
                    cur.execute(SENSITIVITY_SQL, params)
                    for row in cur.fetchall():
                        r = dict(row)
                        r["min_profile_trades"] = min_profile_trades
                        r["min_expectancy"] = min_expectancy
                        rows_all.append(r)

    for row in rows_all:
        baseline_rows = int(row.get("baseline_rows") or 0)
        governance_rows = int(row.get("governance_rows") or 0)
        baseline_pnl = float(row.get("baseline_pnl_points") or 0.0)
        governance_pnl = float(row.get("governance_pnl_points") or 0.0)
        saved = float(row.get("saved_loss_points") or 0.0)
        missed = float(row.get("missed_profit_points") or 0.0)

        pnl_retention = governance_pnl / baseline_pnl if baseline_pnl > 0 else 0.0
        participation = governance_rows / baseline_rows if baseline_rows > 0 else 0.0

        base_exp = row.get("baseline_expectancy")
        gov_exp = row.get("governance_expectancy")
        delta_exp = float(gov_exp) - float(base_exp) if base_exp is not None and gov_exp is not None else None

        print(
            "NG_SENSITIVITY_ROW",
            f"side={row.get('side')}",
            f"min_profile_trades={row.get('min_profile_trades')}",
            f"min_expectancy={float(row.get('min_expectancy')):.6f}",
            f"baseline_rows={baseline_rows}",
            f"governance_rows={governance_rows}",
            f"blocked_rows={row.get('blocked_rows')}",
            f"sample_quality={quality(baseline_rows)}",
            f"participation={participation:.6f}",
            f"baseline_expectancy={fmt(base_exp)}",
            f"governance_expectancy={fmt(gov_exp)}",
            f"delta_expectancy={fmt(delta_exp)}",
            f"baseline_pnl_points={fmt(baseline_pnl)}",
            f"governance_pnl_points={fmt(governance_pnl)}",
            f"pnl_retention={pnl_retention:.6f}",
            f"saved_loss_points={saved:.6f}",
            f"missed_profit_points={missed:.6f}",
            f"governance_alpha_points={(saved - missed):.6f}",
            flush=True,
        )

    # Русский комментарий: кандидат — рост expectancy при сохранении хотя бы 80% baseline PnL.
    candidates = []
    for row in rows_all:
        side = str(row.get("side"))
        baseline_pnl = float(row.get("baseline_pnl_points") or 0.0)
        governance_pnl = float(row.get("governance_pnl_points") or 0.0)
        base_exp = row.get("baseline_expectancy")
        gov_exp = row.get("governance_expectancy")
        if baseline_pnl <= 0 or base_exp is None or gov_exp is None:
            continue

        delta_exp = float(gov_exp) - float(base_exp)
        pnl_retention = governance_pnl / baseline_pnl
        governance_rows = int(row.get("governance_rows") or 0)

        if delta_exp > 0 and pnl_retention >= 0.80 and governance_rows >= 30:
            candidates.append((side, delta_exp, pnl_retention, governance_pnl, row))

    candidates.sort(key=lambda x: (x[0], -x[1], -x[2], -x[3]))

    for rank, (_, delta_exp, pnl_retention, governance_pnl, row) in enumerate(candidates, start=1):
        print(
            "NG_SENSITIVITY_CANDIDATE",
            f"rank={rank}",
            f"side={row.get('side')}",
            f"min_profile_trades={row.get('min_profile_trades')}",
            f"min_expectancy={float(row.get('min_expectancy')):.6f}",
            f"baseline_rows={row.get('baseline_rows')}",
            f"governance_rows={row.get('governance_rows')}",
            f"delta_expectancy={delta_exp:.6f}",
            f"pnl_retention={pnl_retention:.6f}",
            f"baseline_pnl_points={fmt(row.get('baseline_pnl_points'))}",
            f"governance_pnl_points={governance_pnl:.6f}",
            flush=True,
        )

    print("NG_GOVERNANCE_SENSITIVITY_V1_1_OK", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
