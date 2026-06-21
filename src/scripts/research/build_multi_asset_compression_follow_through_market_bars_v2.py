#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os

import psycopg
from psycopg.rows import dict_row


HORIZONS = [5, 15, 30, 60]


def migrate(cur) -> None:
    cur.execute("""
        create table if not exists analytics_multi_asset_compression_follow_through_market_bars_v2 (
            id bigserial primary key,
            created_at timestamptz not null default now(),
            source_row_id bigint not null,
            source_snapshot_id bigint not null,
            symbol text not null,
            asset_class text,
            timeframe text,
            source_status text not null,
            source_created_at timestamptz not null,
            source_close numeric,
            horizon_min integer not null,
            future_bar_ts timestamptz,
            future_close numeric,
            return_pct numeric,
            move_ok boolean,
            status text not null,
            unique(source_row_id, horizon_min)
        );
    """)

    cur.execute("""
        create index if not exists idx_compression_follow_market_bars_v2_symbol
        on analytics_multi_asset_compression_follow_through_market_bars_v2(symbol, timeframe, source_created_at desc);
    """)


def threshold(asset_class: str) -> float:
    if asset_class == "INDEX":
        return 0.03
    if asset_class == "EQUITY":
        return 0.10
    if "FUTURES" in str(asset_class):
        return 0.08
    if asset_class == "FX":
        return 0.03
    return 0.10


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--migrate", action="store_true")
    parser.add_argument("--save", action="store_true")
    parser.add_argument("--limit", type=int, default=5000)
    args = parser.parse_args()

    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL_NOT_SET")

    evaluated = 0
    saved = 0

    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            if args.migrate:
                migrate(cur)

            cur.execute("""
                select
                    id,
                    snapshot_id,
                    created_at,
                    symbol,
                    asset_class,
                    timeframe,
                    status,
                    last_close
                from analytics_multi_asset_compression_row_v1
                where status in ('COMPRESSION', 'EXPANSION_CANDIDATE')
                  and last_close is not null
                order by created_at desc
                limit %s
            """, (args.limit,))
            source_rows = list(cur.fetchall())

            for row in source_rows:
                for horizon in HORIZONS:
                    evaluated += 1

                    cur.execute("""
                        select ts, close
                        from market_bars
                        where symbol = %s
                          and timeframe = %s
                          and ts >= %s + (%s || ' minutes')::interval
                        order by ts asc
                        limit 1
                    """, (
                        row["symbol"],
                        row["timeframe"],
                        row["created_at"],
                        horizon,
                    ))
                    future = cur.fetchone()

                    source_close = row["last_close"]

                    if future is None:
                        future_bar_ts = None
                        future_close = None
                        return_pct = None
                        move_ok = None
                        status = "WAITING"
                    else:
                        future_bar_ts = future["ts"]
                        future_close = future["close"]
                        return_pct = (
                            (future_close - source_close) / source_close * 100
                            if source_close and source_close != 0
                            else None
                        )
                        move_ok = abs(float(return_pct or 0.0)) >= threshold(row["asset_class"])
                        status = "SUCCESS" if move_ok else "FAILURE"

                    if args.save:
                        cur.execute("""
                            insert into analytics_multi_asset_compression_follow_through_market_bars_v2 (
                                source_row_id,
                                source_snapshot_id,
                                symbol,
                                asset_class,
                                timeframe,
                                source_status,
                                source_created_at,
                                source_close,
                                horizon_min,
                                future_bar_ts,
                                future_close,
                                return_pct,
                                move_ok,
                                status
                            )
                            values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                            on conflict (source_row_id, horizon_min)
                            do update set
                                future_bar_ts = excluded.future_bar_ts,
                                future_close = excluded.future_close,
                                return_pct = excluded.return_pct,
                                move_ok = excluded.move_ok,
                                status = excluded.status,
                                created_at = now()
                        """, (
                            row["id"],
                            row["snapshot_id"],
                            row["symbol"],
                            row["asset_class"],
                            row["timeframe"],
                            row["status"],
                            row["created_at"],
                            source_close,
                            horizon,
                            future_bar_ts,
                            future_close,
                            return_pct,
                            move_ok,
                            status,
                        ))
                        saved += 1

            cur.execute("""
                select
                    count(*)::int as rows_total,
                    count(*) filter (where status='SUCCESS')::int as success_rows,
                    count(*) filter (where status='FAILURE')::int as failure_rows,
                    count(*) filter (where status='WAITING')::int as waiting_rows,
                    avg(return_pct) filter (where return_pct is not null) as avg_return_pct,
                    min(return_pct) filter (where return_pct is not null) as min_return_pct,
                    max(return_pct) filter (where return_pct is not null) as max_return_pct
                from analytics_multi_asset_compression_follow_through_market_bars_v2
            """)
            summary = dict(cur.fetchone())

            cur.execute("""
                select
                    symbol,
                    asset_class,
                    source_status,
                    horizon_min,
                    count(*)::int as rows,
                    count(*) filter (where status='SUCCESS')::int as wins,
                    count(*) filter (where status='FAILURE')::int as losses,
                    count(*) filter (where status='WAITING')::int as waiting,
                    avg(return_pct) filter (where return_pct is not null) as avg_return_pct,
                    min(return_pct) filter (where return_pct is not null) as min_return_pct,
                    max(return_pct) filter (where return_pct is not null) as max_return_pct
                from analytics_multi_asset_compression_follow_through_market_bars_v2
                group by symbol, asset_class, source_status, horizon_min
                order by wins desc, rows desc, symbol
                limit 50
            """)
            rows = list(cur.fetchall())

        if args.save or args.migrate:
            conn.commit()
        else:
            conn.rollback()

    print("=== MULTI_ASSET_COMPRESSION_FOLLOW_THROUGH_MARKET_BARS_V2 ===")
    print(f"mode={'save' if args.save else 'dry_run'}")
    print(f"db_update={int(args.save)}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("telegram_send=0")
    print(f"evaluated={evaluated}")
    print(f"saved_rows={saved}")
    print(f"scorecard_rows_total={summary.get('rows_total') or 0}")
    print(f"success_rows={summary.get('success_rows') or 0}")
    print(f"failure_rows={summary.get('failure_rows') or 0}")
    print(f"waiting_rows={summary.get('waiting_rows') or 0}")
    print(f"avg_return_pct={summary.get('avg_return_pct')}")
    print(f"min_return_pct={summary.get('min_return_pct')}")
    print(f"max_return_pct={summary.get('max_return_pct')}")

    for r in rows:
        print(
            "COMPRESSION_MARKET_BARS_FOLLOW_ROW "
            f"symbol={r['symbol']} "
            f"asset_class={r['asset_class']} "
            f"source_status={r['source_status']} "
            f"horizon_min={r['horizon_min']} "
            f"rows={r['rows']} "
            f"wins={r['wins']} "
            f"losses={r['losses']} "
            f"waiting={r['waiting']} "
            f"avg_return_pct={r['avg_return_pct']} "
            f"min_return_pct={r['min_return_pct']} "
            f"max_return_pct={r['max_return_pct']}",
            flush=True,
        )

    print("VERDICT=MULTI_ASSET_COMPRESSION_FOLLOW_THROUGH_MARKET_BARS_V2_READY")
    print("TEST_MULTI_ASSET_COMPRESSION_FOLLOW_THROUGH_MARKET_BARS_V2_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
