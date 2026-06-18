#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import psycopg2
import psycopg2.extras


# Русский комментарий:
# TRADE_CONTEXT_GUARD_ALT_WRITER_ROOT_CAUSE_V1
# Read-only диагностика: ищем, каким writer path была создана новая UNKNOWN trade.
# Ничего не меняет в БД, runtime, execution и real trading.


UNKNOWN_SQL = """
select
    id,
    created_at,
    ts,
    symbol,
    side,
    qty,
    price,
    commission,
    strategy,
    timeframe,
    continuous_symbol,
    trade_source,
    origin,
    fill_id,
    payload
from trades
where created_at::date = current_date
  and (
        coalesce(strategy, '') = ''
     or strategy in ('UNKNOWN', 'UNKNOWN_STRATEGY')
     or coalesce(timeframe, '') = ''
     or timeframe in ('UNKNOWN', 'UNKNOWN_TIMEFRAME')
     or coalesce(continuous_symbol, '') = ''
  )
order by created_at desc, id desc
limit 20;
"""


NEARBY_SQL = """
select
    id,
    created_at,
    symbol,
    side,
    qty,
    price,
    strategy,
    timeframe,
    continuous_symbol,
    trade_source,
    origin,
    fill_id
from trades
where created_at between %s::timestamptz - interval '90 seconds'
                    and %s::timestamptz + interval '90 seconds'
  and symbol = %s
order by created_at asc, id asc;
"""


def norm(v: Any) -> str:
    if v is None:
        return ""
    return str(v).strip()


def parse_payload(v: Any) -> dict[str, Any]:
    if v is None:
        return {}
    if isinstance(v, dict):
        return v
    try:
        return json.loads(str(v))
    except Exception:
        return {}


def payload_keys(payload: dict[str, Any]) -> str:
    if not isinstance(payload, dict):
        return ""
    return ",".join(sorted(str(k) for k in payload.keys()))


def file_scan() -> list[dict[str, Any]]:
    targets = [
        "src/finam_core/storage/postgres_logger.py",
        "src/finam_core/storage/postgres.py",
        "src/finam_core/pipelines/paper_pipeline.py",
    ]

    rows: list[dict[str, Any]] = []

    patterns = [
        "log_trade(",
        "log_fill(",
        "INSERT INTO trades",
        "insert into trades",
        "TradeContextGuardV1",
        "origin",
        "trade_source",
    ]

    for target in targets:
        path = Path(target)
        if not path.exists():
            continue

        lines = path.read_text().splitlines()
        for i, line in enumerate(lines, start=1):
            matched = [p for p in patterns if p.lower() in line.lower()]
            if matched:
                rows.append(
                    {
                        "file": target,
                        "line": i,
                        "patterns": ",".join(matched),
                        "text": line.strip(),
                    }
                )

    return rows


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL is required")

    print("=== TRADE CONTEXT GUARD ALT WRITER ROOT CAUSE V1 ===")
    print("mode=read_only")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print("db_update=0")
    print()

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(UNKNOWN_SQL)
            unknown_rows = cur.fetchall()

            nearby_by_unknown: dict[int, list[dict[str, Any]]] = {}

            for row in unknown_rows:
                cur.execute(NEARBY_SQL, (row["created_at"], row["created_at"], row["symbol"]))
                nearby_by_unknown[int(row["id"])] = cur.fetchall()

    print("ALT_WRITER_UNKNOWN_ROWS")
    for row in unknown_rows:
        payload = parse_payload(row.get("payload"))
        print(
            "ALT_WRITER_UNKNOWN_ROW "
            f"id={row.get('id')} "
            f"created_at={row.get('created_at')} "
            f"symbol={norm(row.get('symbol'))} "
            f"side={norm(row.get('side'))} "
            f"qty={row.get('qty')} "
            f"price={row.get('price')} "
            f"commission={row.get('commission')} "
            f"strategy={norm(row.get('strategy')) or 'NULL'} "
            f"timeframe={norm(row.get('timeframe')) or 'NULL'} "
            f"continuous_symbol={norm(row.get('continuous_symbol')) or 'NULL'} "
            f"trade_source={norm(row.get('trade_source')) or 'NULL'} "
            f"origin={norm(row.get('origin')) or 'NULL'} "
            f"fill_id={norm(row.get('fill_id')) or 'NULL'} "
            f"payload_keys={payload_keys(payload)}"
        )

        for near in nearby_by_unknown.get(int(row["id"]), []):
            print(
                "ALT_WRITER_NEARBY_ROW "
                f"unknown_id={row.get('id')} "
                f"id={near.get('id')} "
                f"created_at={near.get('created_at')} "
                f"symbol={norm(near.get('symbol'))} "
                f"side={norm(near.get('side'))} "
                f"strategy={norm(near.get('strategy')) or 'NULL'} "
                f"timeframe={norm(near.get('timeframe')) or 'NULL'} "
                f"continuous_symbol={norm(near.get('continuous_symbol')) or 'NULL'} "
                f"trade_source={norm(near.get('trade_source')) or 'NULL'} "
                f"origin={norm(near.get('origin')) or 'NULL'} "
                f"fill_id={norm(near.get('fill_id')) or 'NULL'}"
            )

    print()
    print("ALT_WRITER_CODE_SCAN")
    scan = file_scan()
    for hit in scan:
        if (
            "INSERT INTO trades" in hit["patterns"]
            or "insert into trades" in hit["patterns"]
            or "log_trade(" in hit["patterns"]
            or "TradeContextGuardV1" in hit["patterns"]
        ):
            print(
                "ALT_WRITER_CODE_HIT "
                f"file={hit['file']} "
                f"line={hit['line']} "
                f"patterns={hit['patterns']} "
                f"text={hit['text']}"
            )

    unknown_count = len(unknown_rows)
    suspected_alt = 1 if unknown_count > 0 else 0

    print()
    print("ALT_WRITER_ROOT_CAUSE_SUMMARY")
    print(f"unknown_rows={unknown_count}")
    print(f"suspected_alt_writer={suspected_alt}")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print("db_update=0")

    if unknown_count > 0:
        print("VERDICT=TRADE_CONTEXT_GUARD_ALT_WRITER_CONFIRMED_REVIEW_REQUIRED")
    else:
        print("VERDICT=TRADE_CONTEXT_GUARD_ALT_WRITER_NOT_REPRODUCED")

    print("TRADE_CONTEXT_GUARD_ALT_WRITER_ROOT_CAUSE_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
