#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from decimal import Decimal

import psycopg
from psycopg.rows import dict_row


def dec(v):
    if v is None:
        return Decimal("0")
    return Decimal(str(v))


def pf(pos_sum, neg_sum):
    pos_sum = dec(pos_sum)
    neg_sum = abs(dec(neg_sum))
    if neg_sum == 0:
        return None
    return pos_sum / neg_sum


def classify(rows):
    positive = []
    strong = []
    brq = None

    for r in rows:
        pf_value = r["profit_factor_decimal"]
        symbol = r["symbol"]
        if pf_value is None:
            continue
        if pf_value > Decimal("1.0"):
            positive.append(symbol)
        if pf_value >= Decimal("1.2"):
            strong.append(symbol)
        if symbol == "BRQ6@RTSX":
            brq = pf_value

    if brq is not None and brq >= Decimal("3.0") and len(strong) <= 2:
        return "BRQ6_ONLY_ANOMALY"

    if len(strong) >= 4:
        return "BRENT_ROLLOVER_STABLE"

    if len(positive) >= 3:
        return "BRENT_ROLLOVER_PARTIAL"

    return "BRENT_ROLLOVER_NOT_CONFIRMED"


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL_NOT_SET")

    print("=== BRENT_ROLLOVER_EDGE_V1 ===")
    print("mode=research_read_only")
    print("db_update=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("telegram_send=0")
    print("pattern=BOTTOM1+COMPRESSION_RANGE+240m")

    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                with futures_symbols as (
                    select symbol
                    from market_bars
                    where timeframe='M5'
                      and symbol like 'BR%@RTSX'
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
                all_futures_bars as (
                    select
                        mb.symbol,
                        mb.ts,
                        mb.open,
                        mb.high,
                        mb.low,
                        mb.close,
                        row_number() over (partition by mb.symbol order by mb.ts) as rn
                    from market_bars mb
                    where mb.timeframe='M5'
                      and mb.symbol like '%@RTSX'
                      and mb.close is not null
                ),
                features as (
                    select
                        b.*,
                        lag(close, 12) over (partition by symbol order by ts) as close_lookback,
                        max(high) over (
                            partition by symbol order by ts
                            rows between 12 preceding and 1 preceding
                        ) as range_high,
                        min(low) over (
                            partition by symbol order by ts
                            rows between 12 preceding and 1 preceding
                        ) as range_low
                    from all_futures_bars b
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
                    select *
                    from ranked2
                    where bottom_rank = 1
                      and symbols_at_ts >= 5
                      and symbol like 'BR%@RTSX'
                      and range_pct is not null
                      and avg_range_pct_100 is not null
                      and range_pct <= avg_range_pct_100
                ),
                outcomes as (
                    select
                        s.symbol,
                        s.ts as source_ts,
                        s.close as source_close,
                        fb.ts as future_ts,
                        fb.close as future_close,
                        case
                            when fb.close is null or s.close = 0 then null
                            else (fb.close - s.close) / s.close * 100
                        end as return_pct
                    from selected s
                    left join all_futures_bars fb
                      on fb.symbol = s.symbol
                     and fb.rn = s.rn + 48
                )
                select
                    symbol,
                    count(*) filter (where return_pct is not null)::int as observations,
                    count(*) filter (where return_pct > 0)::int as wins,
                    count(*) filter (where return_pct < 0)::int as losses,
                    avg(return_pct) filter (where return_pct is not null) as avg_return_pct,
                    sum(return_pct) filter (where return_pct > 0) as positive_sum,
                    sum(return_pct) filter (where return_pct < 0) as negative_sum,
                    min(source_ts) as first_signal_ts,
                    max(source_ts) as last_signal_ts
                from outcomes
                group by symbol
                having count(*) filter (where return_pct is not null) >= 30
                order by symbol
            """)
            rows = list(cur.fetchall())

    parsed = []
    for r in rows:
        observations = int(r["observations"] or 0)
        wins = int(r["wins"] or 0)
        losses = int(r["losses"] or 0)
        winrate = None if observations == 0 else Decimal(wins) / Decimal(observations)
        pf_value = pf(r["positive_sum"], r["negative_sum"])
        row = dict(r)
        row["profit_factor_decimal"] = pf_value
        parsed.append(row)

        print(
            "BRENT_ROLLOVER_ROW "
            f"symbol={r['symbol']} "
            f"observations={observations} "
            f"wins={wins} "
            f"losses={losses} "
            f"winrate={winrate} "
            f"avg_return_pct={r['avg_return_pct']} "
            f"profit_factor={pf_value} "
            f"first_signal_ts={r['first_signal_ts']} "
            f"last_signal_ts={r['last_signal_ts']}"
        )

    verdict = classify(parsed)

    positive_count = sum(
        1 for r in parsed
        if r["profit_factor_decimal"] is not None and r["profit_factor_decimal"] > Decimal("1.0")
    )
    strong_count = sum(
        1 for r in parsed
        if r["profit_factor_decimal"] is not None and r["profit_factor_decimal"] >= Decimal("1.2")
    )

    print(f"contracts_total={len(parsed)}")
    print(f"positive_contracts={positive_count}")
    print(f"strong_contracts={strong_count}")
    print(f"rollover_verdict={verdict}")

    if parsed:
        print("VERDICT=BRENT_ROLLOVER_EDGE_READY")
    else:
        print("VERDICT=BRENT_ROLLOVER_EDGE_NO_DATA")

    print("TEST_BRENT_ROLLOVER_EDGE_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
