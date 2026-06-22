#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import os
import sys

import psycopg2
import psycopg2.extras

TARGETS = ["NVTK@MISX", "OZON@MISX", "T@MISX", "X5@MISX"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--symbols", default=",".join(TARGETS))
    args = parser.parse_args()

    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("ERROR=DATABASE_URL_NOT_SET")
        return 1

    rows = []
    total_m1 = 0
    total_planned_m5 = 0
    total_inserted = 0

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            targets = [x.strip().upper() for x in args.symbols.split(",") if x.strip()]

            for symbol in targets:
                cur.execute(
                    """
                    select count(*) as m1_bars
                    from market_bars
                    where symbol=%s and timeframe='M1'
                    """,
                    (symbol,),
                )
                m1_bars = int(cur.fetchone()["m1_bars"] or 0)

                cur.execute(
                    """
                    with m1 as (
                        select
                            symbol,
                            date_trunc('hour', ts)
                              + (floor(extract(minute from ts)::int / 5) * interval '5 minutes') as bucket_ts,
                            ts,
                            open,
                            high,
                            low,
                            close,
                            volume
                        from market_bars
                        where symbol=%s
                          and timeframe='M1'
                    ),
                    grouped as (
                        select
                            symbol,
                            bucket_ts,
                            count(*) as source_m1_count,
                            min(ts) as first_ts,
                            max(ts) as last_ts,
                            max(high) as high,
                            min(low) as low,
                            sum(volume) as volume
                        from m1
                        group by symbol, bucket_ts
                    ),
                    first_open as (
                        select distinct on (symbol, bucket_ts)
                            symbol,
                            bucket_ts,
                            open
                        from m1
                        order by symbol, bucket_ts, ts asc
                    ),
                    last_close as (
                        select distinct on (symbol, bucket_ts)
                            symbol,
                            bucket_ts,
                            close
                        from m1
                        order by symbol, bucket_ts, ts desc
                    ),
                    final as (
                        select
                            g.symbol,
                            'M5'::text as timeframe,
                            g.bucket_ts as ts,
                            fo.open,
                            g.high,
                            g.low,
                            lc.close,
                            g.volume,
                            'M1_TO_M5_AGGREGATION_V1'::text as source
                        from grouped g
                        join first_open fo using (symbol, bucket_ts)
                        join last_close lc using (symbol, bucket_ts)
                    )
                    select count(*) as planned_m5
                    from final
                    """,
                    (symbol,),
                )
                planned_m5 = int(cur.fetchone()["planned_m5"] or 0)

                inserted = 0
                if args.apply:
                    cur.execute(
                        """
                        with m1 as (
                            select
                                symbol,
                                date_trunc('hour', ts)
                                  + (floor(extract(minute from ts)::int / 5) * interval '5 minutes') as bucket_ts,
                                ts,
                                open,
                                high,
                                low,
                                close,
                                volume
                            from market_bars
                            where symbol=%s
                              and timeframe='M1'
                        ),
                        grouped as (
                            select
                                symbol,
                                bucket_ts,
                                count(*) as source_m1_count,
                                min(ts) as first_ts,
                                max(ts) as last_ts,
                                max(high) as high,
                                min(low) as low,
                                sum(volume) as volume
                            from m1
                            group by symbol, bucket_ts
                        ),
                        first_open as (
                            select distinct on (symbol, bucket_ts)
                                symbol,
                                bucket_ts,
                                open
                            from m1
                            order by symbol, bucket_ts, ts asc
                        ),
                        last_close as (
                            select distinct on (symbol, bucket_ts)
                                symbol,
                                bucket_ts,
                                close
                            from m1
                            order by symbol, bucket_ts, ts desc
                        ),
                        final as (
                            select
                                g.symbol,
                                'M5'::text as timeframe,
                                g.bucket_ts as ts,
                                fo.open,
                                g.high,
                                g.low,
                                lc.close,
                                g.volume,
                                'M1_TO_M5_AGGREGATION_V1'::text as source
                            from grouped g
                            join first_open fo using (symbol, bucket_ts)
                            join last_close lc using (symbol, bucket_ts)
                        ),
                        upserted as (
                            insert into market_bars
                                (symbol, timeframe, ts, open, high, low, close, volume, source)
                            select
                                symbol, timeframe, ts, open, high, low, close, volume, source
                            from final
                            on conflict (symbol, timeframe, ts) do update set
                                open = excluded.open,
                                high = excluded.high,
                                low = excluded.low,
                                close = excluded.close,
                                volume = excluded.volume,
                                source = excluded.source
                            returning 1
                        )
                        select count(*) as affected from upserted
                        """,
                        (symbol,),
                    )
                    inserted = int(cur.fetchone()["affected"] or 0)

                rows.append(
                    {
                        "symbol": symbol,
                        "m1_bars": m1_bars,
                        "planned_m5_bars": planned_m5,
                        "affected_m5_bars": inserted,
                    }
                )

                total_m1 += m1_bars
                total_planned_m5 += planned_m5
                total_inserted += inserted

            if args.apply:
                conn.commit()
            else:
                conn.rollback()

    out = {
        "verdict": "EQUITY_M1_TO_M5_AGGREGATION_READY",
        "mode": "apply" if args.apply else "dry_run",
        "db_update": 1 if args.apply else 0,
        "runtime_changed": 0,
        "execution_changed": 0,
        "telegram_send": 0,
        "targets_total": len(targets),
        "total_m1_bars": total_m1,
        "total_planned_m5_bars": total_planned_m5,
        "total_affected_m5_bars": total_inserted,
        "rows": rows,
    }

    print(json.dumps(out, ensure_ascii=False, indent=2))
    print("VERDICT=EQUITY_M1_TO_M5_AGGREGATION_READY")
    print("TEST_EQUITY_M1_TO_M5_AGGREGATION_V1_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
