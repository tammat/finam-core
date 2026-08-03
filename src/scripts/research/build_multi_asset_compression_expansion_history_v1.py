#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import os
import subprocess
import sys

import psycopg
from psycopg.rows import dict_row

from marketcore.research_window_guard_v1 import is_market_opening_guard


WATCH_SCRIPT = "src/scripts/research/build_multi_asset_compression_expansion_watch_v1.py"


def run_watch() -> dict:
    proc = subprocess.run(
        [sys.executable, WATCH_SCRIPT],
        cwd="/opt/finam-core",
        capture_output=True,
        text=True,
        timeout=45,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr[-2000:])

    raw = proc.stdout
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end < 0:
        raise RuntimeError("WATCH_JSON_NOT_FOUND")

    return json.loads(raw[start:end + 1])


def migrate(cur) -> None:
    cur.execute("""
        create table if not exists analytics_multi_asset_compression_snapshot_v1 (
            id bigserial primary key,
            created_at timestamptz not null default now(),
            rows_total integer not null default 0,
            equities_total integer not null default 0,
            futures_total integer not null default 0,
            indexes_total integer not null default 0,
            compression_count integer not null default 0,
            expansion_candidate_count integer not null default 0,
            no_setup integer not null default 0,
            no_bars integer not null default 0,
            verdict text not null,
            payload jsonb not null default '{}'::jsonb
        );
    """)

    cur.execute("""
        create table if not exists analytics_multi_asset_compression_row_v1 (
            id bigserial primary key,
            snapshot_id bigint not null references analytics_multi_asset_compression_snapshot_v1(id) on delete cascade,
            created_at timestamptz not null default now(),
            symbol text not null,
            asset_class text,
            timeframe text,
            status text not null,
            bars integer,
            last_close numeric,
            prev_close numeric,
            atr_pct numeric,
            range_pct numeric,
            box_pct numeric,
            volume_ratio numeric,
            trend_pct numeric,
            range_high numeric,
            range_low numeric,
            compression_score numeric,
            expansion_score numeric,
            payload jsonb not null default '{}'::jsonb
        );
    """)

    cur.execute("""
        create index if not exists idx_compression_row_v1_symbol_time
        on analytics_multi_asset_compression_row_v1(symbol, timeframe, created_at desc);
    """)

    cur.execute("""
        create index if not exists idx_compression_row_v1_status_time
        on analytics_multi_asset_compression_row_v1(status, created_at desc);
    """)


def main() -> int:
    if is_market_opening_guard():
        print("MULTI_ASSET_COMPRESSION_HISTORY_DEFERRED reason=PROTECTED_MARKET_OPEN_WINDOW")
        return 0
    parser = argparse.ArgumentParser()
    parser.add_argument("--migrate", action="store_true")
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    print("=== MULTI_ASSET_COMPRESSION_EXPANSION_HISTORY_V1 ===")
    print("mode=save_snapshot" if args.save else "mode=dry_run")
    print("runtime_allow=0")
    print(f"execution_enabled={os.getenv('EXECUTION_ENABLED', '0')}")
    print(f"real_trading_enabled={os.getenv('REAL_TRADING_ENABLED', '0')}")
    print(f"migrate={int(args.migrate)}")
    print(f"db_update={int(args.save)}")
    print("orders_create=0")
    print("execution_intents_create=0")

    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL_NOT_SET")

    watch = run_watch()
    rows = watch.get("rows", [])

    snapshot_id = None
    saved_rows = 0

    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            if args.migrate:
                migrate(cur)

            if args.save:
                cur.execute(
                    """
                    insert into analytics_multi_asset_compression_snapshot_v1 (
                        rows_total,
                        equities_total,
                        futures_total,
                        indexes_total,
                        compression_count,
                        expansion_candidate_count,
                        no_setup,
                        no_bars,
                        verdict,
                        payload
                    )
                    values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    returning id
                    """,
                    (
                        int(watch.get("rows_total") or 0),
                        int(watch.get("equities_total") or 0),
                        int(watch.get("futures_total") or 0),
                        int(watch.get("indexes_total") or 0),
                        int(watch.get("compression_count") or 0),
                        int(watch.get("expansion_candidate_count") or 0),
                        int(watch.get("no_setup") or 0),
                        int(watch.get("no_bars") or 0),
                        str(watch.get("verdict") or "UNKNOWN"),
                        json.dumps(watch, ensure_ascii=False),
                    ),
                )
                snapshot_id = cur.fetchone()["id"]

                for r in rows:
                    cur.execute(
                        """
                        insert into analytics_multi_asset_compression_row_v1 (
                            snapshot_id,
                            symbol,
                            asset_class,
                            timeframe,
                            status,
                            bars,
                            last_close,
                            prev_close,
                            atr_pct,
                            range_pct,
                            box_pct,
                            volume_ratio,
                            trend_pct,
                            range_high,
                            range_low,
                            compression_score,
                            expansion_score,
                            payload
                        )
                        values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        """,
                        (
                            snapshot_id,
                            r.get("symbol"),
                            r.get("asset_class"),
                            r.get("timeframe"),
                            r.get("status"),
                            r.get("bars"),
                            r.get("last_close"),
                            r.get("prev_close"),
                            r.get("atr_pct"),
                            r.get("range_pct"),
                            r.get("box_pct"),
                            r.get("volume_ratio"),
                            r.get("trend_pct"),
                            r.get("range_high"),
                            r.get("range_low"),
                            r.get("compression_score"),
                            r.get("expansion_score"),
                            json.dumps(r, ensure_ascii=False),
                        ),
                    )
                    saved_rows += 1

            cur.execute("select to_regclass('analytics_multi_asset_compression_snapshot_v1') is not null as ok")
            snapshot_table_exists = bool(cur.fetchone()["ok"])

            cur.execute("select to_regclass('analytics_multi_asset_compression_row_v1') is not null as ok")
            row_table_exists = bool(cur.fetchone()["ok"])

            if snapshot_table_exists:
                cur.execute("select count(*)::int as c from analytics_multi_asset_compression_snapshot_v1")
                history_snapshots = cur.fetchone()["c"]
            else:
                history_snapshots = 0

            if row_table_exists:
                cur.execute("select count(*)::int as c from analytics_multi_asset_compression_row_v1")
                history_rows = cur.fetchone()["c"]
            else:
                history_rows = 0

        if args.save or args.migrate:
            conn.commit()
        else:
            conn.rollback()

    print("COMPRESSION_HISTORY_SOURCE")
    print(f"watch_verdict={watch.get('verdict')}")
    print(f"rows_total={watch.get('rows_total')}")
    print(f"compression_count={watch.get('compression_count')}")
    print(f"expansion_candidate_count={watch.get('expansion_candidate_count')}")

    print("COMPRESSION_HISTORY_SUMMARY")
    print(f"snapshot_id={snapshot_id}")
    print(f"saved_rows={saved_rows}")
    print(f"snapshot_table_exists={int(snapshot_table_exists)}")
    print(f"row_table_exists={int(row_table_exists)}")
    print(f"history_snapshots={history_snapshots}")
    print(f"history_rows={history_rows}")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print("real_trading_enabled=0")
    print("execution_enabled=0")
    print("VERDICT=MULTI_ASSET_COMPRESSION_EXPANSION_HISTORY_SAVED" if args.save else "VERDICT=MULTI_ASSET_COMPRESSION_EXPANSION_HISTORY_READY")
    print("MULTI_ASSET_COMPRESSION_EXPANSION_HISTORY_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
