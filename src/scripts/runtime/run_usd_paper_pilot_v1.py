from __future__ import annotations

import argparse
import os

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url
from finam_core.governance.usd_continuous_profile_gate_v1 import UsdContinuousProfileGateV1


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
            partition by symbol order by ts rows between %(lookback)s preceding and 1 preceding
        ) as prev_high,
        min(low) over (
            partition by symbol order by ts rows between %(lookback)s preceding and 1 preceding
        ) as prev_low,
        lead(close, %(horizon)s) over (
            partition by symbol order by ts
        ) as future_close
    from market_bars
    where timeframe = %(timeframe)s
      and symbol = 'USDRUBF@RTSX'
),
signals as (
    select
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
    side,
    hour_msk,
    count(*)::int as profile_trades,
    avg(pnl_points)::float as profile_expectancy
from outcomes
group by side, hour_msk;
"""


LATEST_SIGNAL_SQL = """
with latest as (
    select max(ts) as max_ts
    from market_bars
    where symbol = %(symbol)s
      and timeframe = %(timeframe)s
),
bars as (
    select
        b.symbol,
        b.ts,
        b.close,
        extract(hour from b.ts + interval '3 hours')::int as hour_msk,
        max(b.high) over (
            partition by b.symbol order by b.ts rows between %(lookback)s preceding and 1 preceding
        ) as prev_high,
        min(b.low) over (
            partition by b.symbol order by b.ts rows between %(lookback)s preceding and 1 preceding
        ) as prev_low
    from market_bars b
    where b.symbol = %(symbol)s
      and b.timeframe = %(timeframe)s
)
select
    symbol,
    ts,
    hour_msk,
    close,
    prev_high,
    prev_low,
    case
        when prev_high is not null and close > prev_high then 'BUY'
        when prev_low is not null and close < prev_low then 'SELL'
        else 'NO_SIGNAL'
    end as side
from bars
where ts = (select max_ts from latest);
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default=os.getenv("USD_PAPER_PILOT_SYMBOL", "USDRUBF@RTSX"))
    parser.add_argument("--timeframe", default="M5")
    parser.add_argument("--lookback", type=int, default=20)
    parser.add_argument("--horizon", type=int, default=24)
    parser.add_argument("--min-profile-trades", type=int, default=20)
    parser.add_argument("--min-expectancy", type=float, default=0.0)
    args = parser.parse_args()

    with psycopg.connect(build_psycopg_url(), row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(PROFILE_SQL, {"timeframe": args.timeframe, "lookback": args.lookback, "horizon": args.horizon})
            profiles = {(str(r["side"]), int(r["hour_msk"])): dict(r) for r in cur.fetchall()}

            cur.execute(LATEST_SIGNAL_SQL, {"symbol": args.symbol, "timeframe": args.timeframe, "lookback": args.lookback})
            latest = dict(cur.fetchone() or {})

    side = str(latest.get("side") or "NO_SIGNAL")
    hour_msk = int(latest.get("hour_msk") or -1)
    profile = profiles.get((side, hour_msk), {})

    decision = UsdContinuousProfileGateV1(
        min_profile_trades=args.min_profile_trades,
        min_expectancy=args.min_expectancy,
    ).decide(
        symbol=args.symbol,
        side=side,
        hour_msk=hour_msk,
        profile_trades=int(profile.get("profile_trades") or 0),
        profile_expectancy=profile.get("profile_expectancy"),
    )

    print(
        "USD_PAPER_PILOT_V1_DECISION",
        f"symbol={decision.symbol}",
        f"side={decision.side}",
        f"hour_msk={decision.hour_msk}",
        f"allowed={decision.allowed}",
        "profile=USD_CONTINUOUS_SIDE_HOUR",
        f"profile_trades={decision.profile_trades}",
        f"profile_expectancy={decision.profile_expectancy}",
        f"reason={decision.reason}",
        "paper_only=1",
        flush=True,
    )
    print("USD_PAPER_PILOT_V1_OK", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
