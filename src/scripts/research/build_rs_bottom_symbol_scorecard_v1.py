#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from decimal import Decimal
import psycopg
from psycopg.rows import dict_row


LOOKBACK_BARS = 12


def dec(v):
    return Decimal(str(v)) if v is not None else Decimal("0")


def pf(pos_sum, neg_sum):
    pos_sum = dec(pos_sum)
    neg_sum = abs(dec(neg_sum))
    if neg_sum == 0:
        return None
    return pos_sum / neg_sum


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL_NOT_SET")

    print("=== RS_BOTTOM_SYMBOL_SCORECARD_V1 ===")
    print("mode=research_read_only")
    print("db_update=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("telegram_send=0")

    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                with futures_symbols as (
                    select symbol
                    from market_bars
                    where timeframe='M5'
                      and symbol like '%@RTSX'
                    group by symbol
                    having count(*) >= 500
                ),
                bars as (
                    select
                        mb.symbol,
                        mb.ts,
                        mb.open,
                        mb.high,
                        mb.low,
                        mb.close,
                        row_number() over (partition by mb.symbol order by mb.ts) as rn
                    from market_bars mb
                    join futures_symbols fs on fs.symbol = mb.symbol
                    where mb.timeframe='M5'
                      and mb.close is not null
                ),
                features as (
                    select
                        b.*,
                        lag(close, 12) over (partition by symbol order by ts) as close_lookback,
                        lag(close, 1) over (partition by symbol order by ts) as prev_close,
                        max(high) over (
                            partition by symbol order by ts
                            rows between 12 preceding and 1 preceding
                        ) as range_high,
                        min(low) over (
                            partition by symbol order by ts
                            rows between 12 preceding and 1 preceding
                        ) as range_low
                    from bars b
                ),
                ranked as (
                    select
                        *,
                        case
                            when close_lookback is null or close_lookback = 0 then null
                            else (close - close_lookback) / close_lookback * 100
                        end as rs_return_pct,
                        case
                            when range_low is null or range_low = 0 then null
                            else (range_high - range_low) / range_low * 100
                        end as range_pct,
                        row_number() over (
                            partition by ts
                            order by
                                case
                                    when close_lookback is null or close_lookback = 0 then null
                                    else (close - close_lookback) / close_lookback * 100
                                end asc nulls last
                        ) as bottom_rank,
                        count(*) over (partition by ts) as symbols_at_ts
                    from features
                    where close_lookback is not null
                ),
                ranked2 as (
                    select
                        *,
                        avg(range_pct) over (
                            partition by symbol order by ts
                            rows between 100 preceding and 1 preceding
                        ) as avg_range_pct_100
                    from ranked
                ),
                selected as (
                    select 'BOTTOM1' as selection, * from ranked2
                    where bottom_rank = 1 and symbols_at_ts >= 5

                    union all

                    select 'BOTTOM3' as selection, * from ranked2
                    where bottom_rank <= 3 and symbols_at_ts >= 5
                ),
                filtered as (
                    select 'ALL' as filter_name, * from selected

                    union all

                    select 'COMPRESSION_RANGE' as filter_name, * from selected
                    where range_pct is not null
                      and avg_range_pct_100 is not null
                      and range_pct <= avg_range_pct_100

                    union all

                    select 'REVERSAL_UP_CLOSE' as filter_name, * from selected
                    where prev_close is not null
                      and close > prev_close
                ),
                outcomes as (
                    select
                        f.symbol,
                        f.selection,
                        f.filter_name,
                        h.horizon_min,
                        f.ts as source_ts,
                        f.close as source_close,
                        fb.ts as future_ts,
                        fb.close as future_close,
                        case
                            when fb.close is null or f.close = 0 then null
                            else (fb.close - f.close) / f.close * 100
                        end as return_pct
                    from filtered f
                    cross join (
                        values
                            (60, 12),
                            (240, 48)
                    ) as h(horizon_min, horizon_bars)
                    left join bars fb
                      on fb.symbol = f.symbol
                     and fb.rn = f.rn + h.horizon_bars
                )
                select
                    symbol,
                    selection,
                    filter_name,
                    horizon_min,
                    count(*) filter (where return_pct is not null)::int as observations,
                    count(*) filter (where return_pct > 0)::int as wins,
                    count(*) filter (where return_pct < 0)::int as losses,
                    avg(return_pct) filter (where return_pct is not null) as avg_return_pct,
                    sum(return_pct) filter (where return_pct > 0) as positive_sum,
                    sum(return_pct) filter (where return_pct < 0) as negative_sum
                from outcomes
                group by symbol, selection, filter_name, horizon_min
                having count(*) filter (where return_pct is not null) >= 20
                order by selection, filter_name, horizon_min, symbol
            """)
            rows = list(cur.fetchall())

    best = None

    for r in rows:
        observations = int(r["observations"] or 0)
        wins = int(r["wins"] or 0)
        losses = int(r["losses"] or 0)
        winrate = None if observations == 0 else Decimal(wins) / Decimal(observations)
        pf_value = pf(r["positive_sum"], r["negative_sum"])

        if pf_value is not None and (best is None or pf_value > best[0]):
            best = (pf_value, r)

        print(
            "RS_BOTTOM_SYMBOL_ROW "
            f"symbol={r['symbol']} "
            f"selection={r['selection']} "
            f"filter={r['filter_name']} "
            f"horizon_min={r['horizon_min']} "
            f"observations={observations} "
            f"wins={wins} "
            f"losses={losses} "
            f"winrate={winrate} "
            f"avg_return_pct={r['avg_return_pct']} "
            f"profit_factor={pf_value}"
        )

    print(f"rows_total={len(rows)}")

    if best:
        pf_value, r = best
        print(
            "BEST_RS_BOTTOM_SYMBOL "
            f"symbol={r['symbol']} "
            f"selection={r['selection']} "
            f"filter={r['filter_name']} "
            f"horizon_min={r['horizon_min']} "
            f"profit_factor={pf_value} "
            f"observations={r['observations']}"
        )

    if rows:
        print("VERDICT=RS_BOTTOM_SYMBOL_SCORECARD_READY")
    else:
        print("VERDICT=RS_BOTTOM_SYMBOL_SCORECARD_NO_DATA")

    print("TEST_RS_BOTTOM_SYMBOL_SCORECARD_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
