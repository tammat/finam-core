from __future__ import annotations

import json
import os
import argparse
from pathlib import Path

import psycopg2
import psycopg2.extras


ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = Path(os.getenv(
    "MARKET_DATA_RETENTION_POLICY_PATH",
    ROOT / "config/runtime/market_data_retention_policy_v1.json",
))
DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "MARKET_DATA_RETENTION_ENGINE_V1"


def eligible_id_range(cur, table: str, id_column: str, time_column: str, cutoff_days: int, limit: int):
    cur.execute(
        f"SELECT min({id_column}) low_id,max({id_column}) high_id,count(*) rows FROM ("
        f"SELECT {id_column} FROM {table} WHERE {time_column} < current_date - %s::int "
        f"ORDER BY {id_column} LIMIT %s) q",
        (cutoff_days, limit),
    )
    return cur.fetchone()


def aggregate_ticks(cur, low_id: int, high_id: int, cutoff_days: int, interval_code: str) -> int:
    cur.execute("""
        INSERT INTO analytics.market_tick_aggregate_v1
        (interval_code,bucket_ts,symbol,open_price,high_price,low_price,close_price,
         volume,event_count,source_version)
        SELECT %s,date_bin(%s::interval,ts,timestamptz '2000-01-01'),symbol,
               (array_agg(price ORDER BY ts,id))[1],max(price),min(price),
               (array_agg(price ORDER BY ts DESC,id DESC))[1],sum(volume),count(*),%s
        FROM public.market_ticks
        WHERE id BETWEEN %s AND %s AND ts < current_date - %s::int
        GROUP BY 2,3
        ON CONFLICT(interval_code,bucket_ts,symbol) DO UPDATE SET
          open_price=excluded.open_price,high_price=excluded.high_price,
          low_price=excluded.low_price,close_price=excluded.close_price,
          volume=excluded.volume,event_count=excluded.event_count,
          source_version=excluded.source_version,refreshed_at=now()
    """, (interval_code, interval_code, SOURCE_VERSION, low_id, high_id, cutoff_days))
    return cur.rowcount


def aggregate_microstructure(cur, low_id: int, high_id: int, cutoff_days: int, interval_code: str) -> int:
    cur.execute("""
        INSERT INTO analytics.market_microstructure_aggregate_v1
        (interval_code,bucket_ts,symbol,avg_best_bid,avg_best_ask,avg_spread_bps,
         max_spread_bps,avg_bid_depth,avg_ask_depth,avg_imbalance,snapshot_count,source_version)
        SELECT %s,date_bin(%s::interval,observed_at,timestamptz '2000-01-01'),symbol,
               avg(best_bid),avg(best_ask),avg(spread_bps),max(spread_bps),
               avg(bid_depth),avg(ask_depth),avg(imbalance),count(*),%s
        FROM analytics.market_microstructure_snapshot_v1
        WHERE snapshot_id BETWEEN %s AND %s AND observed_at < current_date - %s::int
        GROUP BY 2,3
        ON CONFLICT(interval_code,bucket_ts,symbol) DO UPDATE SET
          avg_best_bid=excluded.avg_best_bid,avg_best_ask=excluded.avg_best_ask,
          avg_spread_bps=excluded.avg_spread_bps,max_spread_bps=excluded.max_spread_bps,
          avg_bid_depth=excluded.avg_bid_depth,avg_ask_depth=excluded.avg_ask_depth,
          avg_imbalance=excluded.avg_imbalance,snapshot_count=excluded.snapshot_count,
          source_version=excluded.source_version,refreshed_at=now()
    """, (interval_code, interval_code, SOURCE_VERSION, low_id, high_id, cutoff_days))
    return cur.rowcount


def process_source(conn, policy: dict, source: str) -> None:
    cfg = policy["sources"][source]
    table, id_column, column = (
        ("public.market_ticks", "id", "ts") if source == "market_ticks"
        else ("analytics.market_microstructure_snapshot_v1", "snapshot_id", "observed_at")
    )
    cutoff_days = int(cfg["raw_retention_days"])
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        selected = eligible_id_range(
            cur, table, id_column, column, cutoff_days,
            int(policy["maximum_source_rows_per_run"]),
        )
        raw_rows = int(selected["rows"] or 0)
        if raw_rows == 0:
            return
        low_id, high_id = int(selected["low_id"]), int(selected["high_id"])
        aggregate_rows = 0
        for interval_code in cfg["intervals"]:
            aggregate_rows += (
                aggregate_ticks(cur, low_id, high_id, cutoff_days, interval_code)
                if source == "market_ticks"
                else aggregate_microstructure(cur, low_id, high_id, cutoff_days, interval_code)
            )
        if aggregate_rows <= 0:
            raise RuntimeError(f"AGGREGATION_EMPTY:{source}:{low_id}:{high_id}")
        deleted = 0
        if policy["apply_deletes"]:
            cur.execute(
                f"DELETE FROM {table} WHERE {id_column} BETWEEN %s AND %s "
                f"AND {column} < current_date - %s::int",
                (low_id, high_id, cutoff_days),
            )
            deleted = cur.rowcount
            if deleted != raw_rows:
                raise RuntimeError(f"RETENTION_COUNT_MISMATCH:{source}:{raw_rows}:{deleted}")
        print(f"source={source} ids={low_id}:{high_id} raw={raw_rows} aggregates={aggregate_rows} deleted={deleted}")
    conn.commit()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    policy = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    if policy.get("catalog_version") != "MARKET_DATA_RETENTION_POLICY_V1":
        raise RuntimeError("RETENTION_POLICY_VERSION_INVALID")
    if args.dry_run:
        policy["apply_deletes"] = False
    with psycopg2.connect(DB) as conn:
        with conn.cursor() as cur:
            cur.execute("SET statement_timeout=%s", (int(policy["statement_timeout_seconds"]) * 1000,))
        for source in policy["sources"]:
            process_source(conn, policy, source)
        with conn.cursor() as cur:
            for source, cfg in policy["sources"].items():
                aggregate_table = (
                    "analytics.market_tick_aggregate_v1" if source == "market_ticks"
                    else "analytics.market_microstructure_aggregate_v1"
                )
                cur.execute(
                    f"DELETE FROM {aggregate_table} WHERE bucket_ts < current_date - %s::int",
                    (int(cfg["aggregate_retention_days"]),),
                )
        conn.commit()
    print("VERDICT=MARKET_DATA_RETENTION_V1_OK")


if __name__ == "__main__":
    main()
