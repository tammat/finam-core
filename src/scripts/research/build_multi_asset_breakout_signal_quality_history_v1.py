#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row


ROOT = Path("/opt/finam-core")
V2_SCRIPT = "src/scripts/research/build_multi_asset_breakout_watch_v2.py"


def run_v2() -> tuple[int, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    env["FUTURES_PREFIXES"] = env.get("FUTURES_PREFIXES", "BR,NG,GD")
    env["RUNTIME_ALLOW_TRADING"] = "0"
    env["EXECUTION_ENABLED"] = "0"
    env["REAL_TRADING_ENABLED"] = "0"

    result = subprocess.run(
        [sys.executable, V2_SCRIPT],
        cwd=str(ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=45,
    )
    return result.returncode, (result.stdout or "") + "\n" + (result.stderr or "")


def parse_key(output: str, key: str) -> str:
    for line in output.splitlines():
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1].strip()
    return "UNKNOWN"


def parse_field(line: str, key: str) -> str:
    match = re.search(rf"{re.escape(key)}=([^ ]+)", line)
    return match.group(1) if match else "UNKNOWN"


def to_int(value: str) -> int | None:
    if value in {"UNKNOWN", "None", ""}:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def to_bool(value: str) -> bool | None:
    if value in {"1", "true", "True"}:
        return True
    if value in {"0", "false", "False"}:
        return False
    return None


def to_decimal(value: str) -> Decimal | None:
    if value in {"UNKNOWN", "None", ""}:
        return None
    try:
        return Decimal(value)
    except (InvalidOperation, ValueError):
        return None


def parse_rows(output: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in output.splitlines():
        if not line.startswith("MULTI_ASSET_BREAKOUT_WATCH_V2_ROW "):
            continue

        row = {
            "symbol": parse_field(line, "symbol"),
            "asset_class": parse_field(line, "asset_class"),
            "timeframe": parse_field(line, "timeframe"),
            "role": parse_field(line, "role"),
            "ts": parse_field(line, "ts"),
            "close": to_decimal(parse_field(line, "close")),
            "prev_high": to_decimal(parse_field(line, "prev_high")),
            "breakout_ok": to_bool(parse_field(line, "breakout_ok")),
            "atr_pct": to_decimal(parse_field(line, "atr_pct")),
            "atr_min_pct": to_decimal(parse_field(line, "atr_min_pct")),
            "atr_ok": to_bool(parse_field(line, "atr_ok")),
            "volume": to_decimal(parse_field(line, "volume")),
            "avg_volume": to_decimal(parse_field(line, "avg_volume")),
            "volume_ratio": to_decimal(parse_field(line, "volume_ratio")),
            "volume_mult": to_decimal(parse_field(line, "volume_mult")),
            "volume_ok": to_bool(parse_field(line, "volume_ok")),
            "status": parse_field(line, "status"),
            "raw_line": line,
        }
        rows.append(row)

    return rows


def ensure_schema(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS analytics_multi_asset_breakout_snapshot_v1 (
                id BIGSERIAL PRIMARY KEY,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                source TEXT NOT NULL DEFAULT 'MULTI_ASSET_BREAKOUT_WATCH_V2',
                universe_total INTEGER,
                rows_total INTEGER,
                equity_rows INTEGER,
                futures_rows INTEGER,
                no_bars INTEGER,
                breakout_ready INTEGER,
                no_breakout INTEGER,
                atr_blocked INTEGER,
                volume_blocked INTEGER,
                v2_verdict TEXT,
                telegram_decision TEXT,
                execution_enabled BOOLEAN NOT NULL DEFAULT FALSE,
                real_trading_enabled BOOLEAN NOT NULL DEFAULT FALSE,
                db_update BOOLEAN NOT NULL DEFAULT TRUE,
                payload JSONB NOT NULL DEFAULT '{}'::jsonb
            )
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS analytics_multi_asset_breakout_row_v1 (
                id BIGSERIAL PRIMARY KEY,
                snapshot_id BIGINT NOT NULL REFERENCES analytics_multi_asset_breakout_snapshot_v1(id) ON DELETE CASCADE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                symbol TEXT NOT NULL,
                asset_class TEXT,
                timeframe TEXT,
                role TEXT,
                bar_ts TEXT,
                close NUMERIC,
                prev_high NUMERIC,
                breakout_ok BOOLEAN,
                atr_pct NUMERIC,
                atr_min_pct NUMERIC,
                atr_ok BOOLEAN,
                volume NUMERIC,
                avg_volume NUMERIC,
                volume_ratio NUMERIC,
                volume_mult NUMERIC,
                volume_ok BOOLEAN,
                status TEXT,
                raw_line TEXT
            )
            """
        )

        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_multi_asset_breakout_row_v1_symbol_time
            ON analytics_multi_asset_breakout_row_v1(symbol, timeframe, created_at DESC)
            """
        )

        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_multi_asset_breakout_row_v1_status
            ON analytics_multi_asset_breakout_row_v1(status)
            """
        )

        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_multi_asset_breakout_snapshot_v1_created
            ON analytics_multi_asset_breakout_snapshot_v1(created_at DESC)
            """
        )

    conn.commit()


def save_snapshot(conn: psycopg.Connection, output: str, rows: list[dict[str, Any]]) -> int:
    summary = {
        "universe_total": to_int(parse_key(output, "universe_total")),
        "rows_total": to_int(parse_key(output, "rows_total")),
        "equity_rows": to_int(parse_key(output, "equity_rows")),
        "futures_rows": to_int(parse_key(output, "futures_rows")),
        "no_bars": to_int(parse_key(output, "no_bars")),
        "breakout_ready": to_int(parse_key(output, "breakout_ready")),
        "no_breakout": to_int(parse_key(output, "no_breakout")),
        "atr_blocked": to_int(parse_key(output, "atr_blocked")),
        "volume_blocked": to_int(parse_key(output, "volume_blocked")),
        "v2_verdict": parse_key(output, "VERDICT"),
    }

    payload = {
        "saved_at_utc": datetime.now(timezone.utc).isoformat(),
        "raw_summary": summary,
        "rows_count": len(rows),
        "futures_prefixes": os.getenv("FUTURES_PREFIXES", "BR,NG,GD"),
    }

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            INSERT INTO analytics_multi_asset_breakout_snapshot_v1 (
                universe_total,
                rows_total,
                equity_rows,
                futures_rows,
                no_bars,
                breakout_ready,
                no_breakout,
                atr_blocked,
                volume_blocked,
                v2_verdict,
                telegram_decision,
                execution_enabled,
                real_trading_enabled,
                db_update,
                payload
            )
            VALUES (
                %(universe_total)s,
                %(rows_total)s,
                %(equity_rows)s,
                %(futures_rows)s,
                %(no_bars)s,
                %(breakout_ready)s,
                %(no_breakout)s,
                %(atr_blocked)s,
                %(volume_blocked)s,
                %(v2_verdict)s,
                %(telegram_decision)s,
                FALSE,
                FALSE,
                TRUE,
                %(payload)s
            )
            RETURNING id
            """,
            {
                **summary,
                "telegram_decision": "SEND" if (summary["breakout_ready"] or 0) > 0 else "SILENT",
                "payload": json.dumps(payload, ensure_ascii=False),
            },
        )
        snapshot_id = int(cur.fetchone()["id"])

        for row in rows:
            cur.execute(
                """
                INSERT INTO analytics_multi_asset_breakout_row_v1 (
                    snapshot_id,
                    symbol,
                    asset_class,
                    timeframe,
                    role,
                    bar_ts,
                    close,
                    prev_high,
                    breakout_ok,
                    atr_pct,
                    atr_min_pct,
                    atr_ok,
                    volume,
                    avg_volume,
                    volume_ratio,
                    volume_mult,
                    volume_ok,
                    status,
                    raw_line
                )
                VALUES (
                    %(snapshot_id)s,
                    %(symbol)s,
                    %(asset_class)s,
                    %(timeframe)s,
                    %(role)s,
                    %(bar_ts)s,
                    %(close)s,
                    %(prev_high)s,
                    %(breakout_ok)s,
                    %(atr_pct)s,
                    %(atr_min_pct)s,
                    %(atr_ok)s,
                    %(volume)s,
                    %(avg_volume)s,
                    %(volume_ratio)s,
                    %(volume_mult)s,
                    %(volume_ok)s,
                    %(status)s,
                    %(raw_line)s
                )
                """,
                {
                    "snapshot_id": snapshot_id,
                    "symbol": row["symbol"],
                    "asset_class": row["asset_class"],
                    "timeframe": row["timeframe"],
                    "role": row["role"],
                    "bar_ts": row["ts"],
                    "close": row["close"],
                    "prev_high": row["prev_high"],
                    "breakout_ok": row["breakout_ok"],
                    "atr_pct": row["atr_pct"],
                    "atr_min_pct": row["atr_min_pct"],
                    "atr_ok": row["atr_ok"],
                    "volume": row["volume"],
                    "avg_volume": row["avg_volume"],
                    "volume_ratio": row["volume_ratio"],
                    "volume_mult": row["volume_mult"],
                    "volume_ok": row["volume_ok"],
                    "status": row["status"],
                    "raw_line": row["raw_line"],
                },
            )

    conn.commit()
    return snapshot_id


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--migrate", action="store_true")
    parser.add_argument("--save", action="store_true")
    args = parser.parse_args()

    print("=== MULTI ASSET BREAKOUT SIGNAL QUALITY HISTORY V1 ===")
    print("mode=read_only" if not args.save else "mode=save_snapshot")
    print(f"runtime_allow={os.getenv('RUNTIME_ALLOW_TRADING', '0')}")
    print(f"execution_enabled={os.getenv('EXECUTION_ENABLED', '0')}")
    print(f"real_trading_enabled={os.getenv('REAL_TRADING_ENABLED', '0')}")
    print(f"migrate={int(args.migrate)}")
    print(f"db_update={int(args.save)}")
    print("real_execution=0")

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is required")

    code, output = run_v2()
    v2_ok = int(code == 0 and "MULTI_ASSET_BREAKOUT_WATCH_V2_OK" in output)
    rows = parse_rows(output)
    ready_rows = [r for r in rows if "BREAKOUT_READY" in str(r.get("status", ""))]

    snapshot_id: int | None = None

    with psycopg.connect(database_url) as conn:
        if args.migrate:
            ensure_schema(conn)

        if args.save:
            ensure_schema(conn)
            snapshot_id = save_snapshot(conn, output, rows)

        with conn.cursor() as cur:
            cur.execute("SELECT to_regclass('analytics_multi_asset_breakout_snapshot_v1')")
            snapshot_table_exists = cur.fetchone()[0] is not None
            cur.execute("SELECT to_regclass('analytics_multi_asset_breakout_row_v1')")
            row_table_exists = cur.fetchone()[0] is not None

            history_snapshots = 0
            history_rows = 0
            history_ready_rows = 0

            if snapshot_table_exists:
                cur.execute("SELECT count(*) FROM analytics_multi_asset_breakout_snapshot_v1")
                history_snapshots = int(cur.fetchone()[0] or 0)

            if row_table_exists:
                cur.execute("SELECT count(*) FROM analytics_multi_asset_breakout_row_v1")
                history_rows = int(cur.fetchone()[0] or 0)
                cur.execute(
                    """
                    SELECT count(*)
                    FROM analytics_multi_asset_breakout_row_v1
                    WHERE status LIKE '%BREAKOUT_READY%'
                    """
                )
                history_ready_rows = int(cur.fetchone()[0] or 0)

    print()
    print("MULTI_ASSET_BREAKOUT_SIGNAL_QUALITY_HISTORY_SOURCE")
    print(f"v2_ok={v2_ok}")
    print(f"universe_total={parse_key(output, 'universe_total')}")
    print(f"rows_total={parse_key(output, 'rows_total')}")
    print(f"equity_rows={parse_key(output, 'equity_rows')}")
    print(f"futures_rows={parse_key(output, 'futures_rows')}")
    print(f"breakout_ready={parse_key(output, 'breakout_ready')}")
    print(f"no_breakout={parse_key(output, 'no_breakout')}")
    print(f"atr_blocked={parse_key(output, 'atr_blocked')}")
    print(f"volume_blocked={parse_key(output, 'volume_blocked')}")
    print(f"v2_verdict={parse_key(output, 'VERDICT')}")

    print()
    print("MULTI_ASSET_BREAKOUT_SIGNAL_QUALITY_HISTORY_ROWS")
    print(f"parsed_rows={len(rows)}")
    print(f"parsed_ready_rows={len(ready_rows)}")
    print(f"snapshot_id={snapshot_id if snapshot_id is not None else 'NONE'}")
    print(f"snapshot_table_exists={int(snapshot_table_exists)}")
    print(f"row_table_exists={int(row_table_exists)}")
    print(f"history_snapshots={history_snapshots}")
    print(f"history_rows={history_rows}")
    print(f"history_ready_rows={history_ready_rows}")

    print()
    print("MULTI_ASSET_BREAKOUT_SIGNAL_QUALITY_HISTORY_SUMMARY")
    print(f"v2_ok={v2_ok}")
    print(f"db_update={int(args.save)}")
    print(f"migrate={int(args.migrate)}")
    print(f"snapshot_id={snapshot_id if snapshot_id is not None else 'NONE'}")
    print(f"parsed_rows={len(rows)}")
    print(f"parsed_ready_rows={len(ready_rows)}")
    print(f"history_snapshots={history_snapshots}")
    print(f"history_rows={history_rows}")
    print(f"history_ready_rows={history_ready_rows}")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print(f"real_trading_enabled={os.getenv('REAL_TRADING_ENABLED', '0')}")
    print(f"execution_enabled={os.getenv('EXECUTION_ENABLED', '0')}")

    if not v2_ok:
        print("VERDICT=MULTI_ASSET_BREAKOUT_SIGNAL_QUALITY_HISTORY_V2_FAILED")
    elif args.save and snapshot_id is not None and len(rows) > 0:
        print("VERDICT=MULTI_ASSET_BREAKOUT_SIGNAL_QUALITY_HISTORY_SAVED")
    elif not args.save:
        print("VERDICT=MULTI_ASSET_BREAKOUT_SIGNAL_QUALITY_HISTORY_DRY_RUN_READY")
    else:
        print("VERDICT=MULTI_ASSET_BREAKOUT_SIGNAL_QUALITY_HISTORY_REVIEW_REQUIRED")

    print("MULTI_ASSET_BREAKOUT_SIGNAL_QUALITY_HISTORY_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
