#!/usr/bin/env python3
# Русский комментарий: read-only scorecard продолжения движения после сжатия по активным инструментам.
from __future__ import annotations

import os
import psycopg2
from decimal import Decimal


ATR_PCT_MAX = Decimal("0.0025")
FORWARD_BARS = 5
MIN_SIGNALS = 30
MIN_PF = Decimal("1.20")


def d(x):
    return Decimal(str(x or 0))


def main() -> int:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("VERDICT=MULTI_ASSET_COMPRESSION_FOLLOW_THROUGH_NO_DATABASE_URL")
        return 2

    print("=== MULTI_ASSET_COMPRESSION_FOLLOW_THROUGH_SCORECARD_V1 ===")
    print("mode=read_only")
    print("db_update=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("real_trading_enabled=0")
    print(f"compression_atr_pct_max={ATR_PCT_MAX}")
    print(f"forward_bars={FORWARD_BARS}")

    conn = psycopg2.connect(database_url)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                with active_symbols as (
                    select distinct symbol, strategy, timeframe
                    from runtime_active_universe
                    where coalesce(is_enabled, true) = true
                ),
                base as (
                    select
                        b.symbol,
                        coalesce(a.strategy, 'UNKNOWN') as strategy,
                        coalesce(a.timeframe, b.timeframe) as timeframe,
                        b.ts,
                        b.close::numeric as close,
                        b.high::numeric as high,
                        b.low::numeric as low,
                        b.volume::numeric as volume,
                        lag(b.close) over (partition by b.symbol, b.timeframe order by b.ts) as prev_close,
                        lead(b.close, %s) over (partition by b.symbol, b.timeframe order by b.ts) as fwd_close
                    from market_bars b
                    join active_symbols a
                      on a.symbol = b.symbol
                     and a.timeframe = b.timeframe
                    where b.timeframe in ('M1','M5')
                      and b.ts >= now() - interval '30 days'
                ),
                features as (
                    select
                        *,
                        abs(close - prev_close) / nullif(close, 0) as atr_proxy_pct,
                        avg(volume) over (
                            partition by symbol, timeframe
                            order by ts
                            rows between 30 preceding and 1 preceding
                        ) as avg_volume
                    from base
                    where prev_close is not null
                      and fwd_close is not null
                ),
                signals as (
                    select
                        symbol,
                        strategy,
                        timeframe,
                        case when fwd_close >= close then 'BUY' else 'SELL' end as side,
                        close,
                        fwd_close,
                        atr_proxy_pct,
                        volume,
                        avg_volume,
                        case
                            when fwd_close >= close then fwd_close - close
                            else close - fwd_close
                        end as pnl_long_like,
                        fwd_close - close as raw_pnl
                    from features
                    where atr_proxy_pct <= %s
                      and avg_volume is not null
                      and volume <= avg_volume
                )
                select
                    symbol,
                    strategy,
                    timeframe,
                    side,
                    count(*) as signals,
                    avg(raw_pnl) as expectancy,
                    sum(case when raw_pnl > 0 then raw_pnl else 0 end) as gross_win,
                    abs(sum(case when raw_pnl < 0 then raw_pnl else 0 end)) as gross_loss,
                    avg(case when raw_pnl > 0 then 1 else 0 end) as winrate
                from signals
                group by symbol, strategy, timeframe, side
                order by symbol, timeframe, side
                """,
                (FORWARD_BARS, ATR_PCT_MAX),
            )
            rows = cur.fetchall()

        best = None
        total_rows = 0
        positive = 0

        for row in rows:
            symbol, strategy, timeframe, side, signals, expectancy, gross_win, gross_loss, winrate = row
            total_rows += 1
            gw = d(gross_win)
            gl = d(gross_loss)
            pf = None if gl == 0 else gw / gl
            exp = d(expectancy)
            wr = d(winrate)

            if signals >= MIN_SIGNALS and pf is not None and pf >= MIN_PF and exp > 0:
                verdict = "CANDIDATE"
                positive += 1
            else:
                verdict = "REJECT"

            print(
                "SCORE_ROW "
                f"symbol={symbol} strategy={strategy} timeframe={timeframe} side={side} "
                f"signals={signals} expectancy={exp:.6f} "
                f"profit_factor={pf if pf is not None else 'None'} "
                f"winrate={wr:.6f} verdict={verdict}"
            )

            if best is None or exp > best[0]:
                best = (exp, symbol, strategy, timeframe, side, signals, pf, wr)

        print("")
        print("MULTI_ASSET_COMPRESSION_FOLLOW_THROUGH_SCORECARD_SUMMARY")
        print(f"rows={total_rows}")
        print(f"positive_candidates={positive}")
        if best:
            exp, symbol, strategy, timeframe, side, signals, pf, wr = best
            print(
                f"best_symbol={symbol} best_strategy={strategy} best_timeframe={timeframe} "
                f"best_side={side} best_signals={signals} best_expectancy={exp:.6f} "
                f"best_profit_factor={pf if pf is not None else 'None'} best_winrate={wr:.6f}"
            )

        if positive > 0:
            print("VERDICT=MULTI_ASSET_COMPRESSION_FOLLOW_THROUGH_HAS_CANDIDATES")
        else:
            print("VERDICT=MULTI_ASSET_COMPRESSION_FOLLOW_THROUGH_NO_POSITIVE_EDGE")

        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
