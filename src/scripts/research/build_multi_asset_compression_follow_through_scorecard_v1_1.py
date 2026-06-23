#!/usr/bin/env python3
import os
import psycopg2
from decimal import Decimal

DB = os.getenv("DATABASE_URL")
if not DB:
    raise SystemExit("DATABASE_URL is not set")

MIN_SIGNALS = int(os.getenv("MIN_FOLLOW_THROUGH_SIGNALS", "100"))
MIN_PF = Decimal(os.getenv("MIN_FOLLOW_THROUGH_PF", "1.20"))

def fmt(x):
    return "None" if x is None else str(x)

def main():
    print("=== MULTI_ASSET_COMPRESSION_FOLLOW_THROUGH_SCORECARD_V1_1_NO_LOOKAHEAD ===")
    print("mode=read_only")
    print("db_update=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("real_trading_enabled=0")

    sql = """
    with base as (
        select
            symbol,
            'VOLATILITY_BREAKOUT_EQUITY'::text as strategy,
            timeframe,
            ts,
            close::numeric as close,
            lag(close::numeric) over (partition by symbol, timeframe order by ts) as prev_close,
            max(high::numeric) over (
                partition by symbol, timeframe
                order by ts rows between 30 preceding and 1 preceding
            ) as prev_high,
            min(low::numeric) over (
                partition by symbol, timeframe
                order by ts rows between 30 preceding and 1 preceding
            ) as prev_low,
            lead(close::numeric, 5) over (partition by symbol, timeframe order by ts) as fwd_close_5
        from market_bars
        where symbol like '%@MISX'
          and timeframe = 'M5'
    ),
    signals as (
        select
            symbol,
            strategy,
            timeframe,
            case
                when close > prev_high then 'BUY'
                when close < prev_low then 'SELL'
                else null
            end as side,
            close,
            fwd_close_5,
            case
                when close > prev_high then fwd_close_5 - close
                when close < prev_low then close - fwd_close_5
                else null
            end as pnl_5
        from base
        where prev_high is not null
          and prev_low is not null
          and fwd_close_5 is not null
          and (
              close > prev_high
              or close < prev_low
          )
    )
    select
        symbol,
        strategy,
        timeframe,
        side,
        count(*) as signals,
        avg(pnl_5) as expectancy_5,
        case
            when sum(case when pnl_5 < 0 then abs(pnl_5) else 0 end) = 0 then null
            else sum(case when pnl_5 > 0 then pnl_5 else 0 end)
                 / sum(case when pnl_5 < 0 then abs(pnl_5) else 0 end)
        end as profit_factor_5,
        avg(case when pnl_5 > 0 then 1.0 else 0.0 end) as winrate_5
    from signals
    group by symbol, strategy, timeframe, side
    order by symbol, side;
    """

    rows = []
    with psycopg2.connect(DB) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()

    positive = 0
    best = None

    for row in rows:
        symbol, strategy, timeframe, side, signals, expectancy, pf, winrate = row

        verdict = "REJECT"
        if (
            signals >= MIN_SIGNALS
            and expectancy is not None
            and expectancy > 0
            and pf is not None
            and pf >= MIN_PF
        ):
            verdict = "CANDIDATE"
            positive += 1

        if best is None:
            best = row
        else:
            best_exp = best[5] if best[5] is not None else Decimal("-999999")
            cur_exp = expectancy if expectancy is not None else Decimal("-999999")
            if cur_exp > best_exp:
                best = row

        print(
            "SCORE_ROW "
            f"symbol={symbol} strategy={strategy} timeframe={timeframe} side={side} "
            f"signals={signals} expectancy_5={fmt(expectancy)} "
            f"profit_factor_5={fmt(pf)} winrate_5={fmt(winrate)} "
            f"verdict={verdict}"
        )

    print("")
    print("MULTI_ASSET_COMPRESSION_FOLLOW_THROUGH_SCORECARD_V1_1_SUMMARY")
    print(f"rows={len(rows)}")
    print(f"positive_candidates={positive}")

    if best:
        symbol, strategy, timeframe, side, signals, expectancy, pf, winrate = best
        print(
            f"best_symbol={symbol} best_strategy={strategy} best_timeframe={timeframe} "
            f"best_side={side} best_signals={signals} best_expectancy_5={fmt(expectancy)} "
            f"best_profit_factor_5={fmt(pf)} best_winrate_5={fmt(winrate)}"
        )

    if positive > 0:
        print("VERDICT=MULTI_ASSET_COMPRESSION_FOLLOW_THROUGH_HAS_CANDIDATES")
    else:
        print("VERDICT=MULTI_ASSET_COMPRESSION_FOLLOW_THROUGH_NO_POSITIVE_EDGE")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
