#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from decimal import Decimal

import psycopg
from psycopg.rows import dict_row


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

    print("=== EQUITY_RS_BOTTOM_VS_IMOEX_V1 ===")
    print("mode=research_read_only")
    print("db_update=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("telegram_send=0")

    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                with active_equities as (
                    select distinct symbol
                    from runtime_active_universe
                    where is_enabled = true
                      and symbol like '%@MISX'
                ),
                equity_bars as (
                    select
                        mb.symbol,
                        mb.ts,
                        mb.close,
                        row_number() over (partition by mb.symbol order by mb.ts) as rn
                    from market_bars mb
                    join active_equities ae on ae.symbol = mb.symbol
                    where mb.timeframe = 'M5'
                      and mb.close is not null
                ),
                imoex_bars as (
                    select
                        ts,
                        close,
                        lag(close, 12) over (order by ts) as imoex_close_lookback
                    from market_bars
                    where symbol = 'IMOEX'
                      and timeframe = 'M5'
                      and close is not null
                ),
                features as (
                    select
                        eb.symbol,
                        eb.ts,
                        eb.close,
                        eb.rn,
                        lag(eb.close, 12) over (partition by eb.symbol order by eb.ts) as equity_close_lookback,
                        ib.close as imoex_close,
                        ib.imoex_close_lookback
                    from equity_bars eb
                    join imoex_bars ib on ib.ts = eb.ts
                ),
                ranked as (
                    select
                        symbol,
                        ts,
                        close,
                        rn,
                        case
                            when equity_close_lookback is null or equity_close_lookback = 0
                              or imoex_close_lookback is null or imoex_close_lookback = 0
                            then null
                            else
                                ((close - equity_close_lookback) / equity_close_lookback * 100)
                              - ((imoex_close - imoex_close_lookback) / imoex_close_lookback * 100)
                        end as rs_vs_imoex_pct,
                        row_number() over (
                            partition by ts
                            order by
                                case
                                    when equity_close_lookback is null or equity_close_lookback = 0
                                      or imoex_close_lookback is null or imoex_close_lookback = 0
                                    then null
                                    else
                                        ((close - equity_close_lookback) / equity_close_lookback * 100)
                                      - ((imoex_close - imoex_close_lookback) / imoex_close_lookback * 100)
                                end asc nulls last
                        ) as bottom_rank,
                        row_number() over (
                            partition by ts
                            order by
                                case
                                    when equity_close_lookback is null or equity_close_lookback = 0
                                      or imoex_close_lookback is null or imoex_close_lookback = 0
                                    then null
                                    else
                                        ((close - equity_close_lookback) / equity_close_lookback * 100)
                                      - ((imoex_close - imoex_close_lookback) / imoex_close_lookback * 100)
                                end desc nulls last
                        ) as top_rank,
                        count(*) over (partition by ts) as symbols_at_ts
                    from features
                ),
                selected as (
                    select 'BOTTOM1_VS_IMOEX' as selection, * from ranked where bottom_rank = 1 and symbols_at_ts >= 3
                    union all
                    select 'BOTTOM3_VS_IMOEX' as selection, * from ranked where bottom_rank <= 3 and symbols_at_ts >= 3
                    union all
                    select 'TOP1_VS_IMOEX' as selection, * from ranked where top_rank = 1 and symbols_at_ts >= 3
                    union all
                    select 'TOP3_VS_IMOEX' as selection, * from ranked where top_rank <= 3 and symbols_at_ts >= 3
                ),
                outcomes as (
                    select
                        s.selection,
                        s.symbol,
                        s.ts,
                        s.close as source_close,
                        h.horizon_min,
                        fb.ts as future_ts,
                        fb.close as future_close,
                        case
                            when fb.close is null or s.close = 0 then null
                            else (fb.close - s.close) / s.close * 100
                        end as return_pct
                    from selected s
                    cross join (
                        values
                            (60, 12),
                            (240, 48),
                            (1440, 288)
                    ) as h(horizon_min, horizon_bars)
                    left join equity_bars fb
                      on fb.symbol = s.symbol
                     and fb.rn = s.rn + h.horizon_bars
                )
                select
                    selection,
                    horizon_min,
                    count(*) filter (where return_pct is not null)::int as observations,
                    count(*) filter (where return_pct > 0)::int as wins,
                    count(*) filter (where return_pct < 0)::int as losses,
                    avg(return_pct) filter (where return_pct is not null) as avg_return_pct,
                    sum(return_pct) filter (where return_pct > 0) as positive_sum,
                    sum(return_pct) filter (where return_pct < 0) as negative_sum
                from outcomes
                group by selection, horizon_min
                order by selection, horizon_min
            """)
            rows = list(cur.fetchall())

    for r in rows:
        observations = int(r["observations"] or 0)
        wins = int(r["wins"] or 0)
        losses = int(r["losses"] or 0)
        winrate = None if observations == 0 else Decimal(wins) / Decimal(observations)
        pf_value = pf(r["positive_sum"], r["negative_sum"])

        print(
            "EQUITY_RS_VS_IMOEX_ROW "
            f"selection={r['selection']} "
            f"horizon_min={r['horizon_min']} "
            f"observations={observations} "
            f"wins={wins} "
            f"losses={losses} "
            f"winrate={winrate} "
            f"avg_return_pct={r['avg_return_pct']} "
            f"profit_factor={pf_value}"
        )

    print(f"rows_total={len(rows)}")

    if not rows:
        print("VERDICT=EQUITY_RS_BOTTOM_VS_IMOEX_NO_DATA")
    else:
        print("VERDICT=EQUITY_RS_BOTTOM_VS_IMOEX_READY")

    print("TEST_EQUITY_RS_BOTTOM_VS_IMOEX_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
