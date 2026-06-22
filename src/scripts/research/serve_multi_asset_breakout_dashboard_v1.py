#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import os
import psycopg2
import re
import subprocess
import psycopg
from psycopg.rows import dict_row
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path("/opt/finam-core")
PORT = int(os.getenv("MULTI_ASSET_DASHBOARD_PORT", "8088"))
V2_SCRIPT = "src/scripts/research/build_multi_asset_breakout_watch_v2.py"
PLAN_SCRIPT = "src/scripts/research/build_multi_asset_breakout_telegram_notify_plan_v1.py"
JOURNAL_UNIT = "finam-multi-asset-breakout-telegram.service"
MSK = ZoneInfo("Europe/Moscow")



def load_breakout_readiness_scorecard_v1() -> dict:
    # Загружаем scorecard технической готовности к пробою через отдельный read-only builder.
    import json
    import subprocess
    import sys

    cmd = [
        sys.executable,
        "src/scripts/research/build_multi_asset_breakout_breakout_readiness_scorecard_8_equities_v1.py",
    ]

    try:
        proc = subprocess.run(
            cmd,
            cwd="/opt/finam-core",
            capture_output=True,
            text=True,
            timeout=30,
        )
    except Exception as exc:
        return {"verdict": "EDGE_SCORECARD_LOAD_EXCEPTION", "error": str(exc)}

    if proc.returncode != 0:
        return {
            "verdict": "EDGE_SCORECARD_LOAD_FAILED",
            "error": proc.stderr[-1000:],
        }

    raw = proc.stdout
    start = raw.find("{")
    end = raw.rfind("}")

    if start < 0 or end < 0:
        return {"verdict": "EDGE_SCORECARD_JSON_NOT_FOUND"}

    return json.loads(raw[start:end + 1])



def load_compression_history_v1() -> dict:
    # Русский комментарий: читаем историю compression/expansion напрямую из PostgreSQL.
    import os
    import psycopg

    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        return {"verdict": "COMPRESSION_HISTORY_DATABASE_URL_NOT_SET"}

    try:
        with psycopg.connect(dsn, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    select
                      count(*)::int as snapshots,
                      max(created_at) as last_snapshot
                    from analytics_multi_asset_compression_snapshot_v1
                """)
                summary = dict(cur.fetchone())

                cur.execute("""
                    select
                      count(*)::int as rows,
                      count(*) filter (where status='COMPRESSION')::int as compression_rows,
                      count(*) filter (where status='EXPANSION_CANDIDATE')::int as expansion_rows,
                      count(*) filter (where status='NO_SETUP')::int as no_setup_rows,
                      max(created_at) as last_row
                    from analytics_multi_asset_compression_row_v1
                """)
                rows_summary = dict(cur.fetchone())

                cur.execute("""
                    select
                      id,
                      created_at,
                      rows_total,
                      equities_total,
                      futures_total,
                      indexes_total,
                      compression_count,
                      expansion_candidate_count,
                      no_setup,
                      no_bars,
                      verdict
                    from analytics_multi_asset_compression_snapshot_v1
                    order by created_at desc
                    limit 20
                """)
                snapshots = [dict(r) for r in cur.fetchall()]

                cur.execute("""
                    select
                      symbol,
                      asset_class,
                      count(*) filter (where status='COMPRESSION')::int as compression_hits,
                      count(*) filter (where status='EXPANSION_CANDIDATE')::int as expansion_hits,
                      count(*) filter (where status='NO_SETUP')::int as no_setup_hits,
                      max(created_at) as last_seen
                    from analytics_multi_asset_compression_row_v1
                    group by symbol, asset_class
                    order by expansion_hits desc, compression_hits desc, symbol
                    limit 50
                """)
                top_symbols = [dict(r) for r in cur.fetchall()]

        return {
            "verdict": "MULTI_ASSET_COMPRESSION_EXPANSION_HISTORY_DASHBOARD_READY",
            "snapshots": summary.get("snapshots", 0),
            "last_snapshot": summary.get("last_snapshot"),
            "rows": rows_summary.get("rows", 0),
            "compression_rows": rows_summary.get("compression_rows", 0),
            "expansion_rows": rows_summary.get("expansion_rows", 0),
            "no_setup_rows": rows_summary.get("no_setup_rows", 0),
            "last_row": rows_summary.get("last_row"),
            "snapshot_rows": snapshots,
            "top_symbols": top_symbols,
        }
    except Exception as exc:
        return {"verdict": "COMPRESSION_HISTORY_LOAD_FAILED", "error": str(exc)}


def load_compression_expansion_v1() -> dict:
    # Русский комментарий: загружаем compression/expansion через отдельный read-only builder.
    import json
    import subprocess
    import sys

    cmd = [
        sys.executable,
        "src/scripts/research/build_multi_asset_compression_expansion_watch_v1.py",
    ]

    try:
        proc = subprocess.run(
            cmd,
            cwd="/opt/finam-core",
            capture_output=True,
            text=True,
            timeout=30,
        )
    except Exception as exc:
        return {"verdict": "COMPRESSION_EXPANSION_LOAD_EXCEPTION", "error": str(exc)}

    if proc.returncode != 0:
        return {
            "verdict": "COMPRESSION_EXPANSION_LOAD_FAILED",
            "error": proc.stderr[-1000:],
        }

    raw = proc.stdout
    start_json = raw.find("{")
    end_json = raw.rfind("}")

    if start_json < 0 or end_json < 0:
        return {"verdict": "COMPRESSION_EXPANSION_JSON_NOT_FOUND"}

    try:
        return json.loads(raw[start_json:end_json + 1])
    except Exception as exc:
        return {
            "verdict": "COMPRESSION_EXPANSION_JSON_PARSE_FAILED",
            "error": str(exc),
            "raw_tail": raw[-1000:],
        }


def format_msk_time(value: object) -> str:
    """Единый вывод времени на dashboard в московском времени."""
    if value is None:
        return "NONE"

    raw = str(value).strip()
    if not raw or raw.upper() in {"NONE", "NULL"}:
        return "NONE"

    try:
        normalized = raw.replace(" ", "T")
        if normalized.endswith("+00"):
            normalized = normalized + ":00"
        dt = datetime.fromisoformat(normalized)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(MSK).strftime("%Y-%m-%d %H:%M:%S MSK")
    except Exception:
        return raw


def run_cmd(cmd: list[str], env_extra: dict[str, str] | None = None) -> tuple[int, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    env["FUTURES_PREFIXES"] = env.get("FUTURES_PREFIXES", "BR,NG,GD")
    env["RUNTIME_ALLOW_TRADING"] = "0"
    env["EXECUTION_ENABLED"] = "0"
    env["REAL_TRADING_ENABLED"] = "0"
    env["MULTI_ASSET_TELEGRAM_DRY_RUN"] = env.get("MULTI_ASSET_TELEGRAM_DRY_RUN", "1")
    if env_extra:
        env.update(env_extra)

    result = subprocess.run(
        cmd,
        cwd=str(ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
        timeout=30,
    )
    return result.returncode, (result.stdout or "") + "\n" + (result.stderr or "")


def parse_key(output: str, key: str) -> str:
    for line in output.splitlines():
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1].strip()
    return "UNKNOWN"


def parse_field(line: str, key: str) -> str:
    m = re.search(rf"{re.escape(key)}=([^ ]+)", line)
    return m.group(1) if m else "UNKNOWN"


def parse_v2_rows(output: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in output.splitlines():
        if not line.startswith("MULTI_ASSET_BREAKOUT_WATCH_V2_ROW "):
            continue
        rows.append(
            {
                "symbol": parse_field(line, "symbol"),
                "asset_class": parse_field(line, "asset_class"),
                "timeframe": parse_field(line, "timeframe"),
                "role": parse_field(line, "role"),
                "close": parse_field(line, "close"),
                "prev_high": parse_field(line, "prev_high"),
                "breakout_ok": parse_field(line, "breakout_ok"),
                "atr_pct": parse_field(line, "atr_pct"),
                "atr_ok": parse_field(line, "atr_ok"),
                "volume_ratio": parse_field(line, "volume_ratio"),
                "volume_ok": parse_field(line, "volume_ok"),
                "status": parse_field(line, "status"),
                "raw": line,
            }
        )
    return rows



def collect_daily_history() -> dict:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        return {
            "available": 0,
            "error": "DATABASE_URL не задан",
            "snapshots_today": 0,
            "rows_today": 0,
            "ready_today": 0,
            "blockers": {},
            "symbols": [],
        }

    try:
        with psycopg.connect(database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        count(*)::int,
                        min(created_at),
                        max(created_at)
                    FROM analytics_multi_asset_breakout_snapshot_v1
                    WHERE created_at::date = now()::date
                    """
                )
                snapshots_today, first_snapshot, last_snapshot = cur.fetchone()

                cur.execute(
                    """
                    SELECT count(*)::int
                    FROM analytics_multi_asset_breakout_row_v1
                    WHERE created_at::date = now()::date
                    """
                )
                rows_today = int(cur.fetchone()[0] or 0)

                cur.execute(
                    """
                    SELECT count(*)::int
                    FROM analytics_multi_asset_breakout_row_v1
                    WHERE created_at::date = now()::date
                      AND status LIKE '%BREAKOUT_READY%'
                    """
                )
                ready_today = int(cur.fetchone()[0] or 0)

                cur.execute(
                    """
                    SELECT
                        sum(CASE WHEN status LIKE '%NO_BREAKOUT%' THEN 1 ELSE 0 END)::int,
                        sum(CASE WHEN status LIKE '%ATR_TOO_LOW%' THEN 1 ELSE 0 END)::int,
                        sum(CASE WHEN status LIKE '%VOLUME_TOO_LOW%' THEN 1 ELSE 0 END)::int,
                        sum(CASE WHEN status LIKE '%NO_ENOUGH_BARS%' THEN 1 ELSE 0 END)::int
                    FROM analytics_multi_asset_breakout_row_v1
                    WHERE created_at::date = now()::date
                    """
                )
                no_breakout, atr_too_low, volume_too_low, no_enough_bars = cur.fetchone()

                cur.execute(
                    """
                    SELECT
                        symbol,
                        asset_class,
                        timeframe,
                        role,
                        count(*)::int AS observations,
                        sum(CASE WHEN status LIKE '%BREAKOUT_READY%' THEN 1 ELSE 0 END)::int AS ready_count,
                        sum(CASE WHEN status LIKE '%NO_BREAKOUT%' THEN 1 ELSE 0 END)::int AS no_breakout_count,
                        sum(CASE WHEN status LIKE '%ATR_TOO_LOW%' THEN 1 ELSE 0 END)::int AS atr_blocked_count,
                        sum(CASE WHEN status LIKE '%VOLUME_TOO_LOW%' THEN 1 ELSE 0 END)::int AS volume_blocked_count,
                        max(created_at) AS last_seen
                    FROM analytics_multi_asset_breakout_row_v1
                    WHERE created_at::date = now()::date
                    GROUP BY symbol, asset_class, timeframe, role
                    ORDER BY ready_count DESC, observations DESC, symbol, timeframe
                    LIMIT 50
                    """
                )
                symbol_rows = [
                    {
                        "symbol": r[0],
                        "asset_class": r[1],
                        "timeframe": r[2],
                        "role": r[3],
                        "observations": r[4],
                        "ready_count": r[5],
                        "no_breakout_count": r[6],
                        "atr_blocked_count": r[7],
                        "volume_blocked_count": r[8],
                        "last_seen": str(r[9]),
                    }
                    for r in cur.fetchall()
                ]

        return {
            "available": 1,
            "snapshots_today": int(snapshots_today or 0),
            "first_snapshot": str(first_snapshot) if first_snapshot else "NONE",
            "last_snapshot": str(last_snapshot) if last_snapshot else "NONE",
            "rows_today": rows_today,
            "ready_today": ready_today,
            "blockers": {
                "NO_BREAKOUT": int(no_breakout or 0),
                "ATR_TOO_LOW": int(atr_too_low or 0),
                "VOLUME_TOO_LOW": int(volume_too_low or 0),
                "NO_ENOUGH_BARS": int(no_enough_bars or 0),
            },
            "symbols": symbol_rows,
        }
    except Exception as exc:
        return {
            "available": 0,
            "error": f"{type(exc).__name__}: {exc}",
            "snapshots_today": 0,
            "rows_today": 0,
            "ready_today": 0,
            "blockers": {},
            "symbols": [],
        }



def collect_follow_through_scorecard() -> dict:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        return {
            "available": 0,
            "error": "DATABASE_URL не задан",
            "ready_rows": 0,
            "scorecard_rows_total": 0,
            "waiting_rows": 0,
            "horizons": [],
            "symbols": [],
        }

    try:
        with psycopg.connect(database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT count(*)::int
                    FROM analytics_multi_asset_breakout_row_v1
                    WHERE status LIKE '%BREAKOUT_READY%'
                    """
                )
                ready_rows = int(cur.fetchone()[0] or 0)

                cur.execute(
                    """
                    SELECT to_regclass('analytics_multi_asset_breakout_follow_through_v1')
                    """
                )
                scorecard_exists = cur.fetchone()[0] is not None

                if not scorecard_exists:
                    return {
                        "available": 1,
                        "ready_rows": ready_rows,
                        "scorecard_rows_total": 0,
                        "waiting_rows": 0,
                        "horizons": [],
                        "symbols": [],
                    }

                cur.execute(
                    """
                    SELECT count(*)::int
                    FROM analytics_multi_asset_breakout_follow_through_v1
                    """
                )
                scorecard_rows_total = int(cur.fetchone()[0] or 0)

                cur.execute(
                    """
                    SELECT count(*)::int
                    FROM analytics_multi_asset_breakout_follow_through_v1
                    WHERE status = 'WAITING_FUTURE_ROW'
                    """
                )
                waiting_rows = int(cur.fetchone()[0] or 0)

                cur.execute(
                    """
                    SELECT
                        horizon_min,
                        count(*)::int AS rows,
                        sum(CASE WHEN direction_ok IS TRUE THEN 1 ELSE 0 END)::int AS wins,
                        sum(CASE WHEN direction_ok IS FALSE THEN 1 ELSE 0 END)::int AS losses,
                        sum(CASE WHEN status = 'WAITING_FUTURE_ROW' THEN 1 ELSE 0 END)::int AS waiting,
                        avg(return_pct) AS avg_return_pct
                    FROM analytics_multi_asset_breakout_follow_through_v1
                    GROUP BY horizon_min
                    ORDER BY horizon_min
                    """
                )
                horizons = [
                    {
                        "horizon_min": r[0],
                        "rows": r[1],
                        "wins": r[2],
                        "losses": r[3],
                        "waiting": r[4],
                        "avg_return_pct": str(r[5]) if r[5] is not None else "NONE",
                    }
                    for r in cur.fetchall()
                ]

                cur.execute(
                    """
                    SELECT
                        symbol,
                        asset_class,
                        timeframe,
                        role,
                        count(*)::int AS rows,
                        sum(CASE WHEN direction_ok IS TRUE THEN 1 ELSE 0 END)::int AS wins,
                        sum(CASE WHEN direction_ok IS FALSE THEN 1 ELSE 0 END)::int AS losses,
                        sum(CASE WHEN status = 'WAITING_FUTURE_ROW' THEN 1 ELSE 0 END)::int AS waiting,
                        avg(return_pct) AS avg_return_pct,
                        max(ready_created_at) AS last_ready
                    FROM analytics_multi_asset_breakout_follow_through_v1
                    GROUP BY symbol, asset_class, timeframe, role
                    ORDER BY rows DESC, symbol, timeframe
                    LIMIT 50
                    """
                )
                symbols = [
                    {
                        "symbol": r[0],
                        "asset_class": r[1],
                        "timeframe": r[2],
                        "role": r[3],
                        "rows": r[4],
                        "wins": r[5],
                        "losses": r[6],
                        "waiting": r[7],
                        "avg_return_pct": str(r[8]) if r[8] is not None else "NONE",
                        "last_ready": str(r[9]) if r[9] else "NONE",
                    }
                    for r in cur.fetchall()
                ]

        return {
            "available": 1,
            "ready_rows": ready_rows,
            "scorecard_rows_total": scorecard_rows_total,
            "waiting_rows": waiting_rows,
            "horizons": horizons,
            "symbols": symbols,
        }
    except Exception as exc:
        return {
            "available": 0,
            "error": f"{type(exc).__name__}: {exc}",
            "ready_rows": 0,
            "scorecard_rows_total": 0,
            "waiting_rows": 0,
            "horizons": [],
            "symbols": [],
        }



def collect_ready_delivery_stats() -> dict:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        return {
            "available": 0,
            "error": "DATABASE_URL не задан",
            "ready_total": 0,
            "delivery_total": 0,
            "dry_run_total": 0,
            "undelivered_ready": 0,
            "rows": [],
        }

    try:
        with psycopg.connect(database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT count(*)::int
                    FROM analytics_multi_asset_breakout_row_v1
                    WHERE status LIKE '%BREAKOUT_READY%'
                    """
                )
                ready_total = int(cur.fetchone()[0] or 0)

                cur.execute(
                    """
                    SELECT to_regclass('analytics_multi_asset_breakout_ready_delivery_v1')
                    """
                )
                delivery_table_exists = cur.fetchone()[0] is not None

                if not delivery_table_exists:
                    return {
                        "available": 1,
                        "ready_total": ready_total,
                        "delivery_total": 0,
                        "dry_run_total": 0,
                        "undelivered_ready": ready_total,
                        "rows": [],
                    }

                cur.execute(
                    """
                    SELECT count(*)::int
                    FROM analytics_multi_asset_breakout_ready_delivery_v1
                    """
                )
                delivery_total = int(cur.fetchone()[0] or 0)

                cur.execute(
                    """
                    SELECT count(*)::int
                    FROM analytics_multi_asset_breakout_ready_delivery_v1
                    WHERE dry_run IS TRUE
                    """
                )
                dry_run_total = int(cur.fetchone()[0] or 0)

                cur.execute(
                    """
                    SELECT count(*)::int
                    FROM analytics_multi_asset_breakout_row_v1 r
                    LEFT JOIN analytics_multi_asset_breakout_ready_delivery_v1 d
                      ON d.ready_row_id = r.id
                    WHERE r.status LIKE '%BREAKOUT_READY%'
                      AND d.ready_row_id IS NULL
                    """
                )
                undelivered_ready = int(cur.fetchone()[0] or 0)

                cur.execute(
                    """
                    SELECT
                        d.ready_row_id,
                        d.symbol,
                        d.timeframe,
                        d.role,
                        d.delivery_status,
                        d.dry_run,
                        d.delivery_reason,
                        d.created_at AS delivered_at,
                        d.ready_created_at,
                        d.close,
                        d.prev_high,
                        d.status
                    FROM analytics_multi_asset_breakout_ready_delivery_v1 d
                    ORDER BY d.created_at DESC, d.ready_row_id DESC
                    LIMIT 50
                    """
                )
                rows = [
                    {
                        "ready_row_id": r[0],
                        "symbol": r[1],
                        "timeframe": r[2],
                        "role": r[3],
                        "delivery_status": r[4],
                        "dry_run": bool(r[5]),
                        "delivery_reason": r[6],
                        "delivered_at": str(r[7]),
                        "ready_created_at": str(r[8]),
                        "close": str(r[9]),
                        "prev_high": str(r[10]),
                        "status": r[11],
                    }
                    for r in cur.fetchall()
                ]

        return {
            "available": 1,
            "ready_total": ready_total,
            "delivery_total": delivery_total,
            "dry_run_total": dry_run_total,
            "undelivered_ready": undelivered_ready,
            "rows": rows,
        }
    except Exception as exc:
        return {
            "available": 0,
            "error": f"{type(exc).__name__}: {exc}",
            "ready_total": 0,
            "delivery_total": 0,
            "dry_run_total": 0,
            "undelivered_ready": 0,
            "rows": [],
        }


def collect_payload() -> dict:
    v2_code, v2_output = run_cmd([sys.executable, V2_SCRIPT])
    plan_code, plan_output = run_cmd([sys.executable, PLAN_SCRIPT])

    journal_code, journal_output = run_cmd(
        [
            "journalctl",
            "-u",
            JOURNAL_UNIT,
            "--since",
            "30 minutes ago",
            "--no-pager",
        ]
    )

    rows = parse_v2_rows(v2_output)
    ready_rows = [r for r in rows if "BREAKOUT_READY" in r.get("status", "")]

    blocker_counts = {
        "no_breakout": sum("NO_BREAKOUT" in r.get("status", "") for r in rows),
        "atr_too_low": sum("ATR_TOO_LOW" in r.get("status", "") for r in rows),
        "volume_too_low": sum("VOLUME_TOO_LOW" in r.get("status", "") for r in rows),
        "no_enough_bars": sum("NO_ENOUGH_BARS" in r.get("status", "") for r in rows),
    }

    journal_lines = [
        line
        for line in journal_output.splitlines()
        if (
            "MULTI_ASSET_BREAKOUT_TELEGRAM" in line
            or "telegram_decision=" in line
            or "telegram_dry_run=" in line
            or "telegram_sent=" in line
            or "VERDICT=" in line
            or "Traceback" in line
            or "ERROR" in line
        )
    ][-80:]

    rs_bottom_forward = {}
    try:
        dsn = os.getenv("DATABASE_URL")
        if dsn:
            with psycopg2.connect(dsn) as conn:
                rs_bottom_forward = load_rs_bottom_forward(conn)
    except Exception as exc:
        rs_bottom_forward = {
            "error": f"{type(exc).__name__}:{exc}",
            "rows": [],
            "scorecard_rows": [],
        }

    return {
        "dashboard": "MULTI_ASSET_BREAKOUT_SIGNAL_QUALITY_OBSERVATION_V1",
        "mode": "read_only_dashboard",
        "port": PORT,
        "checked_at_msk": datetime.now(MSK).isoformat(),
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "runtime_allow": os.getenv("RUNTIME_ALLOW_TRADING", "0"),
        "execution_enabled": "0",
        "real_trading_enabled": "0",
        "telegram_dry_run": os.getenv("MULTI_ASSET_TELEGRAM_DRY_RUN", "1"),
        "v2_ok": int(v2_code == 0 and "MULTI_ASSET_BREAKOUT_WATCH_V2_OK" in v2_output),
        "plan_ok": int(plan_code == 0 and "MULTI_ASSET_BREAKOUT_TELEGRAM_NOTIFY_PLAN_V1_OK" in plan_output),
        "summary": {
            "universe_total": parse_key(v2_output, "universe_total"),
            "rows_total": parse_key(v2_output, "rows_total"),
            "equity_rows": parse_key(v2_output, "equity_rows"),
            "futures_rows": parse_key(v2_output, "futures_rows"),
            "breakout_ready": parse_key(v2_output, "breakout_ready"),
            "no_breakout": parse_key(v2_output, "no_breakout"),
            "atr_blocked": parse_key(v2_output, "atr_blocked"),
            "volume_blocked": parse_key(v2_output, "volume_blocked"),
            "v2_verdict": parse_key(v2_output, "VERDICT"),
            "telegram_decision": parse_key(plan_output, "telegram_decision"),
            "telegram_send": parse_key(plan_output, "telegram_send"),
            "plan_verdict": parse_key(plan_output, "VERDICT"),
        },
        "blocker_counts": blocker_counts,
        "ready_rows": ready_rows,
        "rows": rows,
        "journal_lines": journal_lines,
        "history_daily": collect_daily_history(),
        "follow_through": collect_follow_through_scorecard(),
        "ready_delivery": collect_ready_delivery_stats(),
        "breakout_readiness_scorecard": load_breakout_readiness_scorecard_v1(),
        "rs_bottom_forward": rs_bottom_forward,
        "compression_expansion": load_compression_expansion_v1(),
        "compression_history": load_compression_history_v1(),
        "db_update": 0,
        "execution_changes_required": 0,
        "runtime_changes_required": 0,
    }



def load_rs_bottom_forward(conn):
    with conn.cursor() as cur:
        cur.execute("""
            select
                selection,
                filter_name,
                signals_total,
                waiting,
                success,
                failure,
                completed,
                profit_factor_forward,
                profit_factor_historical,
                avg_return_pct
            from analytics_futures_rs_bottom_forward_scorecard_v1
            order by profit_factor_historical desc nulls last
        """)

        rows = cur.fetchall()
        cols = [d[0] for d in cur.description]

    return {
        "rows": [dict(zip(cols, r)) for r in rows]
    }

def load_rs_bottom_paper(conn):
    with conn.cursor() as cur:
        cur.execute("""
            select
                count(*)::int as signals_total,
                count(*) filter (where status='WAITING')::int as waiting,
                count(*) filter (where status='SUCCESS')::int as success,
                count(*) filter (where status='FAILURE')::int as failure,
                round(avg(return_pct), 6) as avg_return_pct,
                max(source_ts) as last_signal_time
            from analytics_futures_rs_bottom_paper_observation_v1
        """)
        summary = cur.fetchone()

        cur.execute("""
            select
                symbol, family, selection, filter_name,
                source_ts, source_close, horizon_min,
                future_ts, future_close, return_pct, status
            from analytics_futures_rs_bottom_paper_observation_v1
            order by source_ts desc
            limit 100
        """)
        rows = cur.fetchall()

    return {
        "summary": dict(summary) if summary else {},
        "rows": [dict(r) for r in rows],
    }



def render_html(payload: dict) -> str:
    summary = payload["summary"]
    rows = payload["rows"]
    ready = payload["ready_rows"]
    blockers = payload["blocker_counts"]
    history = payload["history_daily"]
    follow = payload["follow_through"]

    
    def esc(x: object) -> str:
        return html.escape(str(x))

    row_html = "\n".join(
        "<tr>"
        f"<td>{esc(r['symbol'])}</td>"
        f"<td>{esc(r['asset_class'])}</td>"
        f"<td>{esc(r['timeframe'])}</td>"
        f"<td>{esc(r['role'])}</td>"
        f"<td>{esc(r['close'])}</td>"
        f"<td>{esc(r['prev_high'])}</td>"
        f"<td>{esc(r['breakout_ok'])}</td>"
        f"<td>{esc(r['atr_ok'])}</td>"
        f"<td>{esc(r['volume_ok'])}</td>"
        f"<td>{esc(r['status'])}</td>"
        "</tr>"
        for r in rows
    )

    ready_html = "\n".join(
        f"<li>{esc(r['symbol'])} {esc(r['timeframe'])} {esc(r['role'])} close={esc(r['close'])} status={esc(r['status'])}</li>"
        for r in ready
    ) or "<li>Готовых сигналов нет</li>"

    journal_html = "<br>".join(esc(x) for x in payload["journal_lines"][-30:])

    
    follow_horizon_rows = "\n".join(
        "<tr>"
        f"<td>{esc(r.get('horizon_min', ''))}</td>"
        f"<td>{esc(r.get('rows', 0))}</td>"
        f"<td>{esc(r.get('wins', 0))}</td>"
        f"<td>{esc(r.get('losses', 0))}</td>"
        f"<td>{esc(r.get('waiting', 0))}</td>"
        f"<td>{esc(r.get('avg_return_pct', 'NONE'))}</td>"
        "</tr>"
        for r in follow.get("horizons", [])
    ) or "<tr><td colspan='6'>Пока нет BREAKOUT_READY для оценки</td></tr>"

    follow_symbol_rows = "\n".join(
        "<tr>"
        f"<td>{esc(r.get('symbol', ''))}</td>"
        f"<td>{esc(r.get('asset_class', ''))}</td>"
        f"<td>{esc(r.get('timeframe', ''))}</td>"
        f"<td>{esc(r.get('role', ''))}</td>"
        f"<td>{esc(r.get('rows', 0))}</td>"
        f"<td>{esc(r.get('wins', 0))}</td>"
        f"<td>{esc(r.get('losses', 0))}</td>"
        f"<td>{esc(r.get('waiting', 0))}</td>"
        f"<td>{esc(r.get('avg_return_pct', 'NONE'))}</td>"
        f"<td>{esc(r.get('last_ready', 'NONE'))}</td>"
        "</tr>"
        for r in follow.get("symbols", [])
    ) or "<tr><td colspan='10'>Пока нет сигналов для оценки</td></tr>"

    history_symbol_rows = "\n".join(
        "<tr>"
        f"<td>{esc(r.get('symbol', ''))}</td>"
        f"<td>{esc(r.get('asset_class', ''))}</td>"
        f"<td>{esc(r.get('timeframe', ''))}</td>"
        f"<td>{esc(r.get('role', ''))}</td>"
        f"<td>{esc(r.get('observations', 0))}</td>"
        f"<td>{esc(r.get('ready_count', 0))}</td>"
        f"<td>{esc(r.get('no_breakout_count', 0))}</td>"
        f"<td>{esc(r.get('atr_blocked_count', 0))}</td>"
        f"<td>{esc(r.get('volume_blocked_count', 0))}</td>"
        f"<td>{format_msk_time(r.get('last_seen', ''))}</td>"
        "</tr>"
        for r in history.get("symbols", [])
    ) or "<tr><td colspan='10'>История за сегодня пока пуста</td></tr>"


    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Finam Core — наблюдение пробоев</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 24px; background: #111; color: #eee; }}
h1, h2 {{ color: #fff; }}
.card {{ background: #1b1b1b; padding: 16px; margin-bottom: 16px; border-radius: 8px; }}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
th, td {{ border-bottom: 1px solid #333; padding: 6px; text-align: left; }}
th {{ background: #222; }}
.bad {{ color: #ff7777; }}
.good {{ color: #7CFC98; }}
.mono {{ font-family: monospace; font-size: 12px; }}
.menu {{ background: #1b1b1b; padding: 10px; margin-bottom: 16px; border-radius: 8px; }}
.menu a {{ color: #7CFC98; margin-right: 16px; text-decoration: none; font-weight: bold; }}
</style>
</head>
<body>
<h1>Наблюдение качества сигналов пробоя V1</h1>
<nav class="menu">
<a href="#summary">Сводка</a>
<a href="#history">История за день</a>
<a href="#follow">Follow-through</a>
<a href="#blockers">Блокировки</a>
<a href="#ready">Готовые сигналы</a>
<a href="#rows">Текущая таблица</a>
<a href="#journal">Журнал Telegram</a>
<a href="/api/current">Сервисный API</a>
</nav>

<div class="card">
<div>проверено UTC: <span class="mono">{esc(payload["checked_at_utc"])}</span></div>
<div>режим: <span class="mono">{esc(payload["mode"])}</span></div>
<div>исполнение: <span class="good">{esc(payload["execution_enabled"])}</span></div>
<div>реальные сделки: <span class="good">{esc(payload["real_trading_enabled"])}</span></div>
<div>Telegram dry-run: <span class="good">{esc(payload["telegram_dry_run"])}</span></div>
</div>

<div class="card">
<h2 id="summary">Сводка</h2>
<div>инструментов во вселенной: {esc(summary["universe_total"])}</div>
<div>строк наблюдения: {esc(summary["rows_total"])}</div>
<div>акции: {esc(summary["equity_rows"])}</div>
<div>фьючерсы: {esc(summary["futures_rows"])}</div>
<div>готовые пробои: <b>{esc(summary["breakout_ready"])}</b></div>
<div>решение Telegram: <b>{esc(summary["telegram_decision"])}</b></div>
<div>вердикт V2: <span class="mono">{esc(summary["v2_verdict"])}</span></div>
<div>вердикт Telegram-plan: <span class="mono">{esc(summary["plan_verdict"])}</span></div>
</div>


<div class="card">
<h2 id="history">История за день</h2>
<div>снимков сегодня: <b>{esc(history.get("snapshots_today", 0))}</b></div>
<div>строк наблюдения сегодня: <b>{esc(history.get("rows_today", 0))}</b></div>
<div>BREAKOUT_READY сегодня: <b>{esc(history.get("ready_today", 0))}</b></div>
<div>первый снимок: <span class="mono">{format_msk_time(history.get("first_snapshot", "NONE"))}</span></div>
<div>последний снимок: <span class="mono">{format_msk_time(history.get("last_snapshot", "NONE"))}</span></div>
<h3>Причины блокировки — за день</h3>
<div>NO_BREAKOUT: {esc(history.get("blockers", {}).get("NO_BREAKOUT", 0))}</div>
<div>ATR_TOO_LOW: {esc(history.get("blockers", {}).get("ATR_TOO_LOW", 0))}</div>
<div>VOLUME_TOO_LOW: {esc(history.get("blockers", {}).get("VOLUME_TOO_LOW", 0))}</div>
<div>NO_ENOUGH_BARS: {esc(history.get("blockers", {}).get("NO_ENOUGH_BARS", 0))}</div>
<h3>Статистика по инструментам</h3>
<table>
<tr>
<th>Инструмент</th><th>Класс</th><th>ТФ</th><th>Роль</th><th>Наблюдений</th><th>Ready</th>
<th>No breakout</th><th>ATR blocked</th><th>Volume blocked</th><th>Последнее наблюдение, МСК</th>
</tr>
{history_symbol_rows}
</table>
</div>


<div class="card">
<h2 id="follow">Follow-through scorecard</h2>
<div>BREAKOUT_READY всего: <b>{esc(follow.get("ready_rows", 0))}</b></div>
<div>строк scorecard: <b>{esc(follow.get("scorecard_rows_total", 0))}</b></div>
<div>ожидают будущую цену: <b>{esc(follow.get("waiting_rows", 0))}</b></div>

<h3>Горизонты 3/5/10/15 минут</h3>
<table>
<tr>
<th>Горизонт, мин</th><th>Строк</th><th>Успех</th><th>Неуспех</th><th>Ожидание</th><th>Средняя доходность после сигнала</th>
</tr>
{follow_horizon_rows}
</table>

<h3>По инструментам</h3>
<table>
<tr>
<th>Инструмент</th><th>Класс</th><th>ТФ</th><th>Роль</th><th>Строк</th><th>Успех</th><th>Неуспех</th><th>Ожидание</th><th>Средняя доходность после сигнала</th><th>Последний ready, МСК</th>
</tr>
{follow_symbol_rows}
</table>
</div>

<div class="card">
<h2 id="blockers">Причины блокировки — текущий срез</h2>
<div>NO_BREAKOUT: {esc(blockers["no_breakout"])}</div>
<div>ATR_TOO_LOW: {esc(blockers["atr_too_low"])}</div>
<div>VOLUME_TOO_LOW: {esc(blockers["volume_too_low"])}</div>
<div>NO_ENOUGH_BARS: {esc(blockers["no_enough_bars"])}</div>
</div>

<div class="card">
<h2 id="ready">Готовые сигналы BREAKOUT_READY</h2>
<ul>{ready_html}</ul>
</div>

<div class="card">
<h2 id="rows">Текущая таблица наблюдения</h2>
<table>
<tr>
<th>Инструмент</th><th>Класс</th><th>ТФ</th><th>Роль</th><th>Закрытие</th><th>Пред. максимум</th>
<th>Пробой</th><th>ATR</th><th>Объём</th><th>Статус</th>
</tr>
{row_html}
</table>
</div>

<div class="card">
<h2 id="journal">Журнал Telegram sender</h2>
<div class="mono">{journal_html}</div>
</div>


<div class="card">
<h3>Форвардная проверка RS Bottom Scorecard</h3>
<div>Диагностика scorecard: <b>{esc(forward.get('error', 'OK'))}</b></div>
<table>
<tr>
<th>Селекция</th><th>Фильтр</th><th>Всего</th><th>Ожидают</th>
<th>Успешно</th><th>Неуспешно</th><th>Завершено</th>
<th>PF forward</th><th>PF исторический</th><th>Средняя доходность после сигнала</th><th>Вердикт</th>
</tr>
{forward_rows_html}
</table>
</div>

</body>
</html>"""




def safe_load_rs_bottom_paper():
    try:
        dsn = os.getenv("DATABASE_URL")
        if not dsn:
            return {
                "summary": {
                    "signals_total": 0,
                    "waiting": 0,
                    "success": 0,
                    "failure": 0,
                    "avg_return_pct": "",
                    "last_signal_time": "",
                },
                "rows": [],
                "error": "DATABASE_URL_NOT_SET",
            }

        with psycopg.connect(dsn, row_factory=dict_row) as conn:
            return load_rs_bottom_paper(conn)
    except Exception as exc:
        return {
            "summary": {
                "signals_total": 0,
                "waiting": 0,
                "success": 0,
                "failure": 0,
                "avg_return_pct": "",
                "last_signal_time": "",
            },
            "rows": [],
            "error": f"{type(exc).__name__}: {exc}",
        }



def render_page(payload: dict, page: str) -> str:
    def esc(x: object) -> str:
        return html.escape("" if x is None else str(x))

    summary = payload.get("summary", {})
    rows = payload.get("rows", [])
    journal = payload.get("journal_lines", [])
    compression_history = payload.get("compression_history", {})
    breakout_readiness = payload.get("breakout_readiness_scorecard", {})

    body = ""

    if page == "summary":
        body += f"""
<h2>Сводка dashboard</h2>
<div>Вердикт: <b>{esc(summary.get('plan_verdict', summary.get('verdict', '')))}</b></div>
<div>Готовые сигналы: <b>{esc(summary.get('breakout_ready', 0))}</b></div>
<div>Исполнение включено: <b>{esc(summary.get('execution_enabled', 0))}</b></div>
<div>Реальная торговля: <b>{esc(summary.get('real_trading_enabled', 0))}</b></div>
"""

    elif page == "edge":
        body += "<h2>Технический рейтинг готовности</h2>"
        body += "<p>Это не подтверждённое торговое преимущество, а рейтинг близости инструмента к пробою и качества наблюдений.</p>"

        rows = breakout_readiness.get("rows", []) if isinstance(breakout_readiness, dict) else []
        body += """
<table>
<tr>
<th>Инструмент</th><th>Наблюдений</th><th>Близко к пробою</th>
<th>Готовых пробоев</th><th>Нет баров</th><th>Постконтроль</th>
<th>Средняя доходность после сигнала</th><th>Готовность</th><th>Последнее наблюдение</th>
</tr>
"""
        for r in rows:
            body += (
                "<tr>"
                f"<td>{esc(r.get('symbol'))}</td>"
                f"<td>{esc(r.get('observations'))}</td>"
                f"<td>{esc(r.get('close_to_breakout'))}</td>"
                f"<td>{esc(r.get('breakout_ready'))}</td>"
                f"<td>{esc(r.get('no_bars'))}</td>"
                f"<td>{esc(r.get('follow_rows'))}</td>"
                f"<td>{esc(r.get('avg_return_pct'))}</td>"
                f"<td>{esc(r.get('breakout_readiness_score'))}</td>"
                f"<td>{format_msk_time(r.get('last_seen'))}</td>"
                "</tr>"
            )
        body += "</table>"

    elif page == "journal":
        body += "<h2>Журнал Telegram / dashboard</h2>"

        body += """
        <div class="card">
        <b>Журнал системы</b><br>
        Последние события доступны только в административном режиме.
        </div>
        """


    elif page == "compression_history":
        body += "<h2>История сжатия / расширения</h2>"
        body += f"""
<div>Снимков: <b>{esc(compression_history.get('snapshots', 0))}</b></div>
<div>Строк: <b>{esc(compression_history.get('rows', 0))}</b></div>
<div>Сжатие: <b>{esc(compression_history.get('compression_rows', 0))}</b></div>
<div>Расширение: <b>{esc(compression_history.get('expansion_rows', 0))}</b></div>
"""

    else:
        body += f"<h2>Страница {esc(page)}</h2><div class=\"card\">Нет подготовленного представления для этой страницы.</div>"

    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Панель аналитики Finam Core</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 24px; }}
a {{ margin-right: 12px; }}
pre {{ white-space: pre-wrap; }}
</style>
</head>
<body>
<nav>
<a href="/summary">Сводка</a>
<a href="/edge">Техническая готовность к пробою</a>
<a href="/compression-history">История сжатия</a>
<a href="/journal">Журнал</a>
<a href="/rs-bottom-paper">RS Bottom Paper</a>
<a href="/api/current">Сервисный API</a>
</nav>
{body}
</body>
</html>"""

def render_rs_bottom_paper_page(payload: dict) -> str:
    def esc(x: object) -> str:
        return html.escape("" if x is None else str(x))

    paper_summary = {
        "signals_total": 0,
        "waiting": 0,
        "success": 0,
        "failure": 0,
        "avg_return_pct": "",
        "last_signal_time": "",
    }
    paper_rows = []
    scorecard_rows = []
    diagnostic = "OK"

    try:
        import os
        import psycopg
        from psycopg.rows import dict_row

        dsn = os.getenv("DATABASE_URL")
        if not dsn:
            diagnostic = "DATABASE_URL_NOT_SET"
        else:
            with psycopg.connect(dsn, row_factory=dict_row) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        select
                            count(*)::int as signals_total,
                            count(*) filter (where status='WAITING')::int as waiting,
                            count(*) filter (where status='SUCCESS')::int as success,
                            count(*) filter (where status='FAILURE')::int as failure,
                            round(avg(return_pct), 6) as avg_return_pct,
                            max(source_ts) as last_signal_time
                        from analytics_futures_rs_bottom_paper_observation_v1
                    """)
                    paper_summary = dict(cur.fetchone())

                    cur.execute("""
                        select
                            symbol, selection, filter_name, source_ts,
                            source_close, return_pct, status
                        from analytics_futures_rs_bottom_paper_observation_v1
                        order by source_ts desc
                        limit 100
                    """)
                    paper_rows = [dict(r) for r in cur.fetchall()]

                    cur.execute("""
                        select
                            selection, filter_name, signals_total, waiting,
                            success, failure, completed,
                            profit_factor_forward,
                            profit_factor_historical,
                            avg_return_pct,
                            verdict
                        from analytics_futures_rs_bottom_forward_scorecard_v1
                        order by profit_factor_historical desc nulls last
                    """)
                    scorecard_rows = [dict(r) for r in cur.fetchall()]
    except Exception as exc:
        diagnostic = f"{type(exc).__name__}: {exc}"

    paper_rows_html = ""
    for r in paper_rows:
        paper_rows_html += (
            "<tr>"
            f"<td>{esc(r.get('symbol'))}</td>"
            f"<td>{esc(r.get('selection'))}</td>"
            f"<td>{esc(r.get('filter_name'))}</td>"
            f"<td>{format_msk_time(r.get('source_ts'))}</td>"
            f"<td>{esc(r.get('source_close'))}</td>"
            f"<td>{esc(r.get('return_pct'))}</td>"
            f"<td>{esc(r.get('status'))}</td>"
            "</tr>"
        )
    if not paper_rows_html:
        paper_rows_html = "<tr><td colspan='7'>Нет forward-сигналов</td></tr>"

    scorecard_rows_html = ""
    for r in scorecard_rows:
        scorecard_rows_html += (
            "<tr>"
            f"<td>{esc(r.get('selection'))}</td>"
            f"<td>{esc(r.get('filter_name'))}</td>"
            f"<td>{esc(r.get('signals_total'))}</td>"
            f"<td>{esc(r.get('waiting'))}</td>"
            f"<td>{esc(r.get('success'))}</td>"
            f"<td>{esc(r.get('failure'))}</td>"
            f"<td>{esc(r.get('completed'))}</td>"
            f"<td>{esc(r.get('profit_factor_forward'))}</td>"
            f"<td>{esc(r.get('profit_factor_historical'))}</td>"
            f"<td>{esc(r.get('avg_return_pct'))}</td>"
            f"<td>{esc(r.get('verdict'))}</td>"
            "</tr>"
        )
    if not scorecard_rows_html:
        scorecard_rows_html = "<tr><td colspan='11'>Нет данных forward-scorecard</td></tr>"

    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta http-equiv="refresh" content="60">
<title>RS Bottom Paper</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 24px; }}
.card {{ border: 1px solid #ddd; border-radius: 8px; padding: 16px; margin-bottom: 16px; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #ddd; padding: 6px 8px; }}
th {{ background: #f3f3f3; }}
a {{ margin-right: 12px; }}
</style>
</head>
<body>
<nav>
<a href="/summary">Сводка</a>
<a href="/compression-history">История сжатия</a>
<a href="/edge">Техническая готовность к пробою</a>
<a href="/rs-bottom-paper">RS Bottom Paper</a>
<a href="/api/current">Сервисный API</a>
</nav>

<div class="card">
<h2>RS Bottom Paper</h2>
<div>Автообновление страницы: <b>60 секунд</b></div>
<div>Всего сигналов: <b>{esc(paper_summary.get('signals_total'))}</b></div>
<div>Ожидают: <b>{esc(paper_summary.get('waiting'))}</b></div>
<div>Успешно: <b>{esc(paper_summary.get('success'))}</b></div>
<div>Неуспешно: <b>{esc(paper_summary.get('failure'))}</b></div>
<div>Средняя доходность после сигнала: <b>{esc(paper_summary.get('avg_return_pct'))}</b></div>
<div>Последний сигнал, МСК: <b>{format_msk_time(paper_summary.get('last_signal_time'))}</b></div>
<div>Диагностика: <b>{esc(diagnostic)}</b></div>
</div>

<div class="card">
<h3>Форвардная проверка RS Bottom Scorecard</h3>
<table>
<tr>
<th>Селекция</th><th>Фильтр</th><th>Всего</th><th>Ожидают</th>
<th>Успешно</th><th>Неуспешно</th><th>Завершено</th>
<th>PF forward</th><th>PF исторический</th><th>Средняя доходность после сигнала</th><th>Вердикт</th>
</tr>
{scorecard_rows_html}
</table>
</div>

<div class="card">
<h3>Сигналы форвардной проверки</h3>
<table>
<tr>
<th>Инструмент</th><th>Селекция</th><th>Фильтр</th>
<th>Время сигнала</th><th>Цена сигнала</th><th>Доходность %</th><th>Статус</th>
</tr>
{paper_rows_html}
</table>
</div>
</body>
</html>"""



def render_rs_bottom_forward_leaderboard_page(payload: dict | None = None) -> str:
    import html

    def esc(v):
        return html.escape("" if v is None else str(v))

    rs = {}
    if payload:
        rs = payload.get("rs_bottom_forward", {}) or {}

    rows = rs.get("scorecard_rows", []) or rs.get("rows", []) or []

    def pf(x):
        try:
            return float(x or 0)
        except Exception:
            return 0.0

    def quality(row):
        completed = int(row.get("completed") or 0)
        success = int(row.get("success") or 0)
        failure = int(row.get("failure") or 0)
        pf_forward = pf(row.get("profit_factor_forward"))

        anomaly = pf_forward > 50 or failure == 0

        if anomaly:
            return 0.0, "⚠ Статистическая аномалия"
        if completed >= 20 and success >= 3 and failure >= 1 and pf_forward >= 1.2:
            score = min(completed, 50) * 0.4 + min(success, 20) * 0.3 + min(pf_forward, 10) * 0.3
            return score, "🟢 Подтверждённый кандидат"
        if completed >= 10 and success >= 3 and pf_forward >= 1.0:
            score = min(completed, 50) * 0.25 + min(success, 20) * 0.25 + min(pf_forward, 10) * 0.2
            return score, "🟡 Перспективный кандидат"

        return min(completed, 50) * 0.1, "⚪ Наблюдение"

    leaders = sorted(rows, key=lambda r: quality(r)[0], reverse=True)

    cards = []
    for i, r in enumerate(leaders[:10], start=1):
        completed = int(r.get("completed") or 0)
        pf_forward = pf(r.get("profit_factor_forward"))
        quality_score, status = quality(r)

        cards.append(f"""
        <div class="card">
          <h3>#{i} {esc(r.get('selection'))} / {esc(r.get('filter_name'))}</h3>
          <div><b>Статус:</b> {status}</div>
          <div><b>Quality score:</b> {esc(round(quality_score, 4))}</div>
          <div><b>PF форвардной проверки:</b> {esc(r.get('profit_factor_forward'))}</div>
          <div><b>PF исторический:</b> {esc(r.get('profit_factor_historical'))}</div>
          <div><b>Завершено:</b> {esc(completed)}</div>
          <div><b>Ожидает:</b> {esc(r.get('waiting'))}</div>
          <div><b>Успешно:</b> {esc(r.get('success'))}</div>
          <div><b>Неуспешно:</b> {esc(r.get('failure'))}</div>
          <div><b>Средняя доходность:</b> {esc(r.get('avg_return_pct'))}</div>
        </div>
        """)

    if not cards:
        cards.append("<div class='card'>Нет данных форвардной проверки.</div>")

    conclusion = """
    <div class="card">
      <h2>Выводы</h2>
      <p><b>Главный вывод:</b> первые форвардные наблюдения уже появились, поэтому проект перешёл от поиска гипотез к проверке торгового преимущества.</p>
      <p><b>Кандидаты:</b> приоритет имеют строки RS Bottom с selection=BOTTOM3 и фильтрами REVERSAL_UP_CLOSE / COMPRESSION_RANGE.</p>
      <p><b>Ограничение:</b> высокий PF forward пока не означает готовность к реальной торговле. Требуется устойчивость на большем числе завершённых наблюдений, контроль комиссий, проскальзывания и out-of-sample.</p>
      <p><b>Решение:</b> реальные сделки не включать. Продолжать накопление forward-статистики.</p>
    </div>
    """

    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Лидеры исследований</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 14px; background: #fafafa; color: #111; }}
.card {{ background: white; border: 1px solid #ddd; border-radius: 12px; padding: 12px; margin: 10px 0; }}
.nav a {{ display: inline-block; margin: 4px 8px 8px 0; }}
</style>
</head>
<body>\n{dashboard_nav_ru('Лидеры исследований')}
<div class="nav">
<a href="/mobile">Главная</a>
<a href="/leaderboard">Лидеры исследований</a>
<a href="/edge-stability">Устойчивость преимущества</a>
<a href="/rs-bottom-clean">RS Bottom очищенный</a>
<a href="/leaderboard">Лидеры</a> <a href="/rs-bottom-forward">Форвардная проверка RS Bottom</a>
<a href="/edge">Готовность к пробою</a>
</div>

<h1>🏆 Лидеры исследований</h1>
{conclusion}
{''.join(cards)}
</body>
</html>"""

def render_rs_bottom_forward_page(payload: dict) -> str:
    def esc(x):
        import html
        return html.escape("" if x is None else str(x))

    rs = payload.get("rs_bottom_forward", {})
    rows = rs.get("rows", [])

    table_rows = ""
    for r in rows:
        table_rows += (
            "<tr>"
            f"<td>{esc(r.get('selection'))}</td>"
            f"<td>{esc(r.get('filter_name'))}</td>"
            f"<td>{esc(r.get('signals_total'))}</td>"
            f"<td>{esc(r.get('waiting'))}</td>"
            f"<td>{esc(r.get('success'))}</td>"
            f"<td>{esc(r.get('failure'))}</td>"
            f"<td>{esc(r.get('completed'))}</td>"
            f"<td>{esc(r.get('profit_factor_forward'))}</td>"
            f"<td>{esc(r.get('profit_factor_historical'))}</td>"
            f"<td>{esc(r.get('avg_return_pct'))}</td>"
            f"<td>{esc(r.get('verdict'))}</td>"
            "</tr>"
        )

    if not table_rows:
        table_rows = "<tr><td colspan='11'>Нет данных forward scorecard</td></tr>"

    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta http-equiv="refresh" content="60">
<title>Форвардная проверка RS Bottom</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 24px; }}
.card {{ border: 1px solid #ddd; border-radius: 8px; padding: 16px; margin-bottom: 16px; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #ddd; padding: 6px 8px; }}
th {{ background: #f3f3f3; }}
a {{ margin-right: 12px; }}
</style>
</head>
<body>
<nav>
<a href="/summary">Сводка</a>
<a href="/rs-bottom-paper">RS Bottom Paper</a>
<a href="/rs-bottom-forward">Форвардная проверка RS Bottom</a>
<a href="/edge">Технический рейтинг</a>
<a href="/api/current">Сервисный API</a>
</nav>

<div class="card">
<h2>Форвардная проверка RS Bottom Accumulation</h2>
<div>Автообновление: <b>60 секунд</b></div>
<div>Диагностика: <b>{esc(rs.get('diagnostic'))}</b></div>
<div>Завершено total: <b>{esc(rs.get('completed_total'))}</b></div>
<div>Вердикт: <b>{esc(rs.get('verdict'))}</b></div>
</div>

<div class="card">
<table>
<tr>
<th>Селекция</th><th>Фильтр</th><th>Всего</th><th>Ожидают</th>
<th>Успешно</th><th>Неуспешно</th><th>Завершено</th>
<th>PF форвардной проверки</th><th>PF исторический</th><th>Средняя доходность</th><th>Вердикт строки</th>
</tr>
{table_rows}
</table>
</div>
</body>
</html>"""




def render_rs_breakout_confirmation_page(payload: dict | None = None) -> str:
    def esc(x):
        import html
        return html.escape("" if x is None else str(x))

    rows = []
    diagnostic = "OK"
    verdict = "RS_BREAKOUT_CONFIRMATION_COLLECTING"

    try:
        import os
        import psycopg
        from psycopg.rows import dict_row

        dsn = os.getenv("DATABASE_URL")
        if not dsn:
            raise RuntimeError("DATABASE_URL_NOT_SET")

        with psycopg.connect(dsn, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    with rs as (
                        select
                            id, symbol, selection, filter_name,
                            source_ts, return_pct, status
                        from analytics_futures_rs_bottom_paper_observation_v1
                        where status in ('SUCCESS','FAILURE','WAITING')
                    ),
                    breakout_confirm as (
                        select
                            rs.id as rs_id,
                            count(*)::int as breakout_rows,
                            min(br.created_at) as first_breakout_time
                        from rs
                        join analytics_multi_asset_breakout_row_v1 br
                          on br.symbol = rs.symbol
                         and br.created_at >= rs.source_ts
                         and br.created_at <= rs.source_ts + interval '240 minutes'
                         and (br.status = 'BREAKOUT_READY' or br.breakout_ok = true)
                        group by rs.id
                    ),
                    classified as (
                        select
                            rs.*,
                            case when bc.rs_id is not null then 'RS_PLUS_BREAKOUT' else 'RS_ONLY' end as bucket,
                            bc.breakout_rows,
                            bc.first_breakout_time
                        from rs
                        left join breakout_confirm bc on bc.rs_id = rs.id
                    )
                    select
                        bucket,
                        selection,
                        filter_name,
                        count(*)::int as observations,
                        count(*) filter (where status='WAITING')::int as waiting,
                        count(*) filter (where status in ('SUCCESS','FAILURE'))::int as completed,
                        count(*) filter (where status='SUCCESS')::int as wins,
                        count(*) filter (where status='FAILURE')::int as losses,
                        avg(return_pct) filter (where status in ('SUCCESS','FAILURE')) as avg_return_pct,
                        sum(return_pct) filter (where status='SUCCESS') as positive_sum,
                        sum(return_pct) filter (where status='FAILURE') as negative_sum
                    from classified
                    group by bucket, selection, filter_name
                    order by bucket, selection, filter_name
                """)
                rows = [dict(r) for r in cur.fetchall()]

        for r in rows:
            pos = r.get("positive_sum") or 0
            neg = abs(r.get("negative_sum") or 0)
            r["profit_factor"] = None if neg == 0 else pos / neg

            completed = int(r.get("completed") or 0)
            pf = r["profit_factor"]

            if completed < 10:
                r["row_verdict"] = "НЕДОСТАТОЧНО_ДАННЫХ"
            elif pf is None:
                r["row_verdict"] = "НЕТ_PF"
            elif pf >= 1.30:
                r["row_verdict"] = "ПОДТВЕРЖДЕНИЕ_УЛУЧШАЕТ_EDGE"
            elif pf >= 1.00:
                r["row_verdict"] = "ПОДТВЕРЖДЕНИЕ_СЛАБОЕ"
            else:
                r["row_verdict"] = "ПОДТВЕРЖДЕНИЕ_НЕ_УЛУЧШАЕТ_EDGE"

        if any(r.get("bucket") == "RS_PLUS_BREAKOUT" for r in rows):
            verdict = "RS_BREAKOUT_CONFIRMATION_HAS_CONFIRMATIONS"

    except Exception as exc:
        diagnostic = f"{type(exc).__name__}: {exc}"
        rows = []
        verdict = "ERROR"

    table_rows = ""
    for r in rows:
        table_rows += (
            "<tr>"
            f"<td>{esc(r.get('bucket'))}</td>"
            f"<td>{esc(r.get('selection'))}</td>"
            f"<td>{esc(r.get('filter_name'))}</td>"
            f"<td>{esc(r.get('observations'))}</td>"
            f"<td>{esc(r.get('waiting'))}</td>"
            f"<td>{esc(r.get('completed'))}</td>"
            f"<td>{esc(r.get('wins'))}</td>"
            f"<td>{esc(r.get('losses'))}</td>"
            f"<td>{esc(r.get('avg_return_pct'))}</td>"
            f"<td>{esc(r.get('profit_factor'))}</td>"
            f"<td>{esc(r.get('row_verdict'))}</td>"
            "</tr>"
        )

    if not table_rows:
        table_rows = "<tr><td colspan='11'>Нет данных RS подтверждение пробоем</td></tr>"

    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta http-equiv="refresh" content="60">
<title>RS подтверждение пробоем</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 24px; }}
.card {{ border: 1px solid #ddd; border-radius: 8px; padding: 16px; margin-bottom: 16px; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #ddd; padding: 6px 8px; }}
th {{ background: #f3f3f3; }}
a {{ margin-right: 12px; }}
</style>
</head>
<body>
<nav>
<a href="/summary">Сводка</a>
<a href="/rs-bottom-paper">RS Bottom Paper</a>
<a href="/rs-bottom-forward">Форвардная проверка RS Bottom</a>
<a href="/rs-breakout-confirmation">RS подтверждение пробоем</a>
<a href="/edge">Технический рейтинг</a>
<a href="/api/current">Сервисный API</a>
</nav>

<div class="card">
<h2>RS подтверждение пробоем</h2>
<div>Автообновление: <b>60 секунд</b></div>
<div>Диагностика: <b>{esc(diagnostic)}</b></div>
<div>Окно подтверждения: <b>240 минут</b></div>
<div>Строк: <b>{esc(len(rows))}</b></div>
<div>Вердикт: <b>{esc(verdict)}</b></div>
</div>

<div class="card">
<table>
<tr>
<th>Корзина</th><th>Селекция</th><th>Фильтр</th><th>Наблюдений</th>
<th>Ожидают</th><th>Завершено</th><th>Успешно</th><th>Неуспешно</th>
<th>Средняя доходность</th><th>PF</th><th>Вердикт строки</th>
</tr>
{table_rows}
</table>
</div>
</body>
</html>"""




def render_mobile_research_summary_page(payload: dict | None = None) -> str:
    def esc(x):
        import html
        return html.escape("" if x is None else str(x))

    futures = [
        ("🟢", "RS Bottom Futures", "🟢 Главный кандидат", "PF исторический 1.5233", "Форвардная проверка: ожидают=2, завершено=0"),
        ("🟡", "RS + подтверждение пробоем", "🟡 Сбор статистики", "PF форвардная проверка: нет", "Ждём завершённых наблюдений"),
        ("🔴", "NG: пробой", "ОТКЛОНЕНО", "PF < 1", "Комиссии съели результат"),
        ("🔴", "BR: пробой", "ИССЛЕДОВАНИЕ ЗАВЕРШЕНО", "готовность к пробою не подтверждена", "Не допускать к реальной торговле"),
        ("⛔", "USDRUB Regime", "ЗАБЛОКИРОВАНО", "Отрицательный результат", "Остановлено через runtime guard"),
    ]

    equities = [
        ("🟡", "Акции: RS Bottom Absolute", "СЛАБЫЙ ЭФФЕКТ", "BOTTOM1 60м PF 1.0443", "Недостаточно для стратегии"),
        ("🔴", "Акции: RS vs IMOEX", "ОТРИЦАТЕЛЬНО", "BOTTOM1 60м PF 0.9065", "Фильтр ухудшил результат"),
        ("⚪", "Акции: Пробой волатильности", "НАБЛЮДЕНИЕ", "готовность к пробою не подтверждена", "Сигналы блокируются фильтрами"),
        ("⚪", "Акции: Мультиактивный пробой", "🟡 Сбор данных", "готовых пробоев=0", "Нужна статистика"),
    ]

    def cards(rows):
        out = ""
        for icon, name, status, metric, note in rows:
            out += f"""
<div class="card">
  <div class="title"><span class="icon">{esc(icon)}</span> {esc(name)}</div>
  <div class="status">{esc(status)}</div>
  <div class="metric">{esc(metric)}</div>
  <div class="note">{esc(note)}</div>
</div>
"""
        return out

    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="60">
<title>Finam Core — мобильная сводка</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 12px; background: #fafafa; color: #111; }}
h1 {{ font-size: 22px; margin: 8px 0 12px; }}
h2 {{ font-size: 18px; margin: 18px 0 8px; }}
.card {{ background: white; border: 1px solid #ddd; border-radius: 12px; padding: 12px; margin: 8px 0; }}
.title {{ font-weight: bold; font-size: 16px; }}
.icon {{ font-size: 18px; }}
.status {{ margin-top: 6px; font-weight: bold; }}
.metric {{ margin-top: 6px; }}
.note {{ margin-top: 6px; color: #555; font-size: 14px; }}
.nav a {{ display: inline-block; margin: 4px 8px 8px 0; }}
.legend {{ font-size: 13px; color: #555; line-height: 1.45; }}
</style>
</head>
<body>

<div class="card">
  <h2>📈 Монитор пробоя</h2>
  <div>Техническая готовность инструментов к пробою. Это не подтверждённое торговое преимущество.</div>
  <div><a href="/edge">Открыть техническую готовность к пробою</a></div>
</div>

<div class="card">
  <h2>🧪 Исследование преимущества</h2>
  <div>RS Bottom Futures, форвардные наблюдения и источник потенциального преимущества.</div>
  <div><a href="/leaderboard">Лидеры исследований</a></div>
  <div><a href="/edge-stability">Устойчивость преимущества</a></div>
  <div><a href="/rs-bottom-forward">Форвардная проверка RS Bottom</a></div>
  <div><a href="/rs-bottom-clean">RS Bottom очищенный</a></div>
  <div><a href="/rs-breakout-confirmation">RS + пробой</a></div>
  <div><a href="/brent-rollover-edge">Переносимость Brent</a></div>
</div>

<div class="card">
  <h2>🟢 Состояние системы</h2>
  <div>Панель аналитики, данные, исследовательский контур, исполнение и реальные сделки.</div>
  <div>Исполнение: выключено. Реальные сделки: выключены.</div>
</div>

<div class="nav">
<a href="/mobile">Главная</a>
<a href="/summary">Техсводка</a>
<a href="/rs-bottom-forward">RS: форвардная проверка</a>
<a href="/rs-breakout-confirmation">RS + пробой</a>
<a href="/api/current">API</a>
</div>

<h1>Finam Core: мобильная сводка</h1>

<div class="card">
  <div class="title">Индикаторы</div>
  <div class="legend">🟢 перспективно / 🟡 сбор статистики / 🔴 отрицательно / ⚪ наблюдение / ⛔ заблокировано</div>
</div>

<div class="card">
  <div class="title">Общий статус проекта</div>
  <div class="metric">Инфраструктура: 95%</div>
  <div class="metric">Панель аналитики: 95%</div>
  <div class="metric">Research: 95%</div>
  <div class="metric">Реальная торговля: 25%</div>
  <div class="note">Главный блокер: нет форвардного подтверждения потенциального преимущества.</div>
</div>


<div class="card">
  <div class="title">🟢 ТЕКУЩИЙ КАНДИДАТ НА EDGE</div>
  <div class="status">RS Bottom Futures</div>
  <div class="metric">Исторический PF: 1.5233</div>
  <div class="metric">Форвардная проверка: ожидают=2, успех=0, ошибка=0, завершено=0</div>
  <div class="note">Статус: ожидание форвардного подтверждения.</div>
</div>

<div class="card">
  <div class="title">📊 Источник потенциального преимущества</div>
  <div class="metric">🥇 BRQ6 — PF 5.15</div>
  <div class="metric">🥈 NGV6 — PF 3.03</div>
  <div class="metric">🥉 GLM6 — PF 2.14</div>
  <div class="note">Вердикт: CONTRACT_SPECIFIC_ANOMALY. Требуется форвардная проверка.</div>
</div>

<div class="card">
  <div class="title">🎯 Следующий контроль</div>
  <div class="status">RS_BOTTOM_FIRST_COMPLETED_FORWARD_V1</div>
  <div class="note">Условие: success + failure >= 1. После события пересчитать PF_forward.</div>
</div>

<h2>Фьючерсы</h2>
{cards(futures)}

<h2>Акции</h2>
{cards(equities)}

<div class="card">
  <div class="title">Следующий контроль</div>
  <div class="status">RS_BOTTOM_FIRST_COMPLETED_FORWARD_V1</div>
  <div class="note">Условие: success + failure >= 1</div>
</div>

</body>
</html>"""






def dashboard_nav_ru(active: str = "") -> str:
    """Единое пользовательское меню dashboard 8088."""
    items = [
        ("/mobile", "🏠 Главная"),
        ("/leaderboard", "Лидеры исследований"),
        ("/edge-stability", "Устойчивость преимущества"),
        ("/rs-bottom-clean", "RS Bottom очищенный"),
        ("/equities", "Акции"),
        ("/rs-bottom-forward", "Форвардная проверка RS Bottom"),
        ("/rs-breakout-confirmation", "RS + пробой"),
        ("/brent-rollover-edge", "Brent rollover"),
        ("/compression-history", "История сжатия"),
    ]

    links = []
    for href, title in items:
        cls = " style='font-weight:bold;text-decoration:underline;'" if title == active else ""
        links.append(f"<a{cls} href='{href}'>{title}</a>")

    return "<div class='nav'>" + " ".join(links) + "</div>"


def fmt_dashboard_number(v, digits: int = 3):
    try:
        if v is None or v == "":
            return ""
        return f"{float(v):.{digits}f}"
    except Exception:
        return "" if v is None else str(v)



def render_equities_dashboard_v1(payload: dict | None = None) -> str:
    import html
    import os
    import psycopg2

    def esc(v):
        return html.escape("" if v is None else str(v))

    dsn = os.getenv("DATABASE_URL")
    rows = []
    error = ""
    clean_runtime = 0
    legacy_runtime = 0

    if dsn:
        try:
            import subprocess
            import re

            audit = subprocess.run(
                [
                    "/opt/finam-core/venv/bin/python3",
                    "src/scripts/research/build_equities_clean_trade_source_audit_v1.py",
                ],
                cwd="/opt/finam-core",
                text=True,
                capture_output=True,
                timeout=60,
            )
            audit_raw = (audit.stdout or "") + "\n" + (audit.stderr or "")
            m = re.search(r"clean_runtime=(\d+) .*legacy_or_unknown=(\d+)", audit_raw)
            if m:
                clean_runtime = int(m.group(1))
                legacy_runtime = int(m.group(2))
        except Exception:
            pass

    if dsn:
        try:
            with psycopg2.connect(dsn) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        with universe as (
                            select
                                symbol,
                                strategy,
                                timeframe
                            from runtime_active_universe
                            where symbol like '%%@MISX'
                        ),
                        bars as (
                            select
                                symbol,
                                count(*) filter (where timeframe='M1')::int as m1_bars,
                                count(*) filter (where timeframe='M5')::int as m5_bars,
                                max(ts) as last_bar_ts
                            from market_bars
                            where symbol like '%%@MISX'
                            group by symbol
                        )
                        select
                            u.symbol,
                            u.strategy,
                            u.timeframe,
                            coalesce(b.m1_bars, 0) as m1_bars,
                            coalesce(b.m5_bars, 0) as m5_bars,
                            b.last_bar_ts
                        from universe u
                        left join bars b on b.symbol=u.symbol
                        order by u.symbol
                    """)
                    rows = cur.fetchall()
        except Exception as exc:
            error = f"{type(exc).__name__}: {exc}"

    table_rows = ""
    for r in rows:
        symbol, strategy, timeframe, m1, m5, last_ts = r

        if not last_ts:
            status = "🔴 Нет баров"
        else:
            status = "⚪ Сбор статистики"

        table_rows += f"""
        <tr>
          <td>{esc(symbol)}</td>
          <td>{esc(strategy)}</td>
          <td>{esc(timeframe)}</td>
          <td>{esc(m1)}</td>
          <td>{esc(m5)}</td>
          <td>{esc(last_ts)}</td>
          <td>{status}</td>
        </tr>
        """

    if not table_rows:
        table_rows = "<tr><td colspan='7'>Нет активных акций или есть ошибка чтения схемы.</td></tr>"

    error_html = f"<div class='card'><b>Диагностика:</b> {esc(error)}</div>" if error else ""

    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Акции</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 14px; background: #fafafa; color: #111; }}
.card {{ background: white; border: 1px solid #ddd; border-radius: 12px; padding: 12px; margin: 10px 0; }}
.nav a {{ display: inline-block; margin: 4px 8px 8px 0; }}
table {{ border-collapse: collapse; width: 100%; font-size: 13px; background: white; }}
th, td {{ border: 1px solid #ddd; padding: 6px; text-align: left; }}
th {{ background: #f3f3f3; }}
.bad {{ color: #a00000; font-weight: bold; }}
</style>
</head>
<body>
{dashboard_nav_ru("Акции")}

<h1>Акции</h1>

<div class="card">
  <h2>Статус направления</h2>
  <div><b>Режим:</b> сбор статистики</div>
  <div><b>Стратегия:</b> VOLATILITY_BREAKOUT_EQUITY</div>
  <div><b>Реальная торговля:</b> <span class="bad">запрещена</span></div>
</div>

{error_html}

<div class="card">
  <h2>Классификация сделок</h2>
  <div><b>Чистые runtime сделки:</b> {clean_runtime}</div>
  <div><b>Legacy/Fallback сделки:</b> {legacy_runtime}</div>
  <div><b>Вывод:</b> исторические и legacy-сделки не используются для оценки edge по VOLATILITY_BREAKOUT_EQUITY.</div>
</div>

<div class="card">
  <h2>Активная вселенная акций</h2>
  <table>
    <tr>
      <th>Инструмент</th>
      <th>Стратегия</th>
      <th>ТФ</th>
      <th>Баров M1</th>
      <th>Баров M5</th>
      <th>Последний бар</th>
      <th>Статус</th>
    </tr>
    {table_rows}
  </table>
</div>

<div class="card">
  <h2>Вывод</h2>
  <p>Раздел акций находится в режиме наблюдения. Реальная торговля отключена. Основной контроль: наличие баров и накопление статистики.</p>
</div>

</body>
</html>"""

def render_rs_bottom_clean_subset_dashboard_v1(payload: dict | None = None) -> str:
    import html
    import os
    import re
    import subprocess

    def esc(v):
        return html.escape("" if v is None else str(v))

    env = os.environ.copy()
    env.setdefault("RUNTIME_ALLOW_TRADING", "0")
    env.setdefault("EXECUTION_ENABLED", "0")
    env.setdefault("REAL_TRADING_ENABLED", "0")

    proc = subprocess.run(
        [
            "/opt/finam-core/venv/bin/python3",
            "src/scripts/research/build_rs_bottom_clean_subset_replay_v1.py",
        ],
        cwd="/opt/finam-core",
        env=env,
        text=True,
        capture_output=True,
        timeout=60,
    )

    raw = (proc.stdout or "") + "\n" + (proc.stderr or "")

    acc_proc = subprocess.run(
        [
            "/opt/finam-core/venv/bin/python3",
            "src/scripts/research/build_rs_bottom_clean_subset_forward_accumulation_v1.py",
        ],
        cwd="/opt/finam-core",
        env=env,
        text=True,
        capture_output=True,
        timeout=60,
    )

    acc_raw = (acc_proc.stdout or "") + "\n" + (acc_proc.stderr or "")
    accumulation = {}
    for acc_line in acc_raw.splitlines():
        if acc_line.startswith("ACCUMULATION_ROW "):
            accumulation = dict(re.findall(r"([a-zA-Z_]+)=([^ ]+)", acc_line))

    summary = {}
    symbols = []

    for line in raw.splitlines():
        if line.startswith("CLEAN_SUBSET_ROW "):
            summary = dict(re.findall(r"([a-zA-Z_]+)=([^ ]+)", line))
        elif line.startswith("CLEAN_SYMBOL_ROW "):
            symbols.append(dict(re.findall(r"([a-zA-Z_]+)=([^ ]+)", line)))

    brn6 = next((r for r in symbols if r.get("symbol") == "BRN6@RTSX"), {})

    symbol_rows = ""
    for r in symbols:
        symbol_rows += f"""
        <tr>
          <td>{esc(r.get('symbol'))}</td>
          <td>{esc(r.get('completed'))}</td>
          <td>{esc(r.get('success'))}</td>
          <td>{esc(r.get('failure'))}</td>
          <td>{esc(fmt_dashboard_number(r.get('real_pf')))}</td>
          <td>{esc(fmt_dashboard_number(r.get('expectancy')))}</td>
        </tr>
        """

    if not symbol_rows:
        symbol_rows = "<tr><td colspan='6'>Нет данных по инструментам.</td></tr>"

    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>RS Bottom — очищенная версия</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 14px; background: #fafafa; color: #111; }}
.card {{ background: white; border: 1px solid #ddd; border-radius: 12px; padding: 12px; margin: 10px 0; }}
.nav a {{ display: inline-block; margin: 4px 8px 8px 0; }}
table {{ border-collapse: collapse; width: 100%; font-size: 13px; background: white; }}
th, td {{ border: 1px solid #ddd; padding: 6px; text-align: left; }}
th {{ background: #f3f3f3; }}
.bad {{ color: #a00000; font-weight: bold; }}
.warn {{ color: #9a6a00; font-weight: bold; }}
</style>
</head>
<body>
{dashboard_nav_ru("RS Bottom очищенный")}
<div class="card"><b>Навигация:</b> Главная → RS Bottom очищенный</div>

<h1>RS Bottom — очищенная версия</h1>

<div class="card">
  <h2>Статус исследования</h2>
  <div><b>Полная версия:</b> <span class="bad">отклонена</span></div>
  <div><b>Очищенная версия:</b> <span class="warn">исследовательский кандидат</span></div>
  <div><b>Реальная торговля:</b> <span class="bad">запрещена</span></div>
</div>

<div class="card">
  <h2>Что исключено</h2>
  <div>NG-контракты: исключены</div>
  <div>Фильтр сжатия: исключён</div>
  <div>12:00 МСК: исключено</div>
</div>

<div class="card">
  <h2>Очищенная выборка</h2>
  <div><b>Всего сигналов:</b> {esc(summary.get('signals'))}</div>
  <div><b>Ожидают завершения:</b> {esc(summary.get('waiting'))}</div>
  <div><b>Завершено наблюдений:</b> {esc(summary.get('completed'))}</div>
  <div><b>Успешно:</b> {esc(summary.get('success'))}</div>
  <div><b>Неуспешно:</b> {esc(summary.get('failure'))}</div>
  <div><b>Доля успешных:</b> {esc(fmt_dashboard_number(summary.get('winrate')))}</div>
  <div><b>Реальный коэффициент прибыли:</b> {esc(fmt_dashboard_number(summary.get('real_pf')))}</div>
  <div><b>Математическое ожидание:</b> {esc(fmt_dashboard_number(summary.get('expectancy')))}</div>
</div>

<div class="card">
  <h2>Лучший инструмент</h2>
  <div><b>Инструмент:</b> {esc(brn6.get('symbol', 'BRN6@RTSX'))}</div>
  <div><b>Завершено:</b> {esc(brn6.get('completed'))}</div>
  <div><b>Успешно:</b> {esc(brn6.get('success'))}</div>
  <div><b>Неуспешно:</b> {esc(brn6.get('failure'))}</div>
  <div><b>Реальный коэффициент прибыли:</b> {esc(fmt_dashboard_number(brn6.get('real_pf')))}</div>
  <div><b>Математическое ожидание:</b> {esc(fmt_dashboard_number(brn6.get('expectancy')))}</div>
</div>

<div class="card">
  <h2>Инструменты очищенной выборки</h2>
  <table>
    <tr>
      <th>Инструмент</th>
      <th>Завершено</th>
      <th>Успешно</th>
      <th>Неуспешно</th>
      <th>Реальный коэффициент прибыли</th>
      <th>Математическое ожидание</th>
    </tr>
    {symbol_rows}
  </table>
</div>

<div class="card">
  <h2>Накопление статистики</h2>
  <div><b>Цель завершённых наблюдений:</b> {esc(accumulation.get('target_completed', 100))}</div>
  <div><b>Сейчас завершено:</b> {esc(accumulation.get('completed'))}</div>
  <div><b>Осталось до цели:</b> {esc(accumulation.get('remaining'))}</div>
  <div><b>Реальный коэффициент прибыли:</b> {esc(fmt_dashboard_number(accumulation.get('real_pf')))}</div>
  <div><b>Математическое ожидание:</b> {esc(fmt_dashboard_number(accumulation.get('expectancy')))}</div>
  <div><b>Решение:</b> продолжать накопление статистики</div>
  <div><b>Реальная торговля:</b> <span class="bad">запрещена</span></div>
</div>

<div class="card">
  <h2>Ограничение</h2>
  <p>Очищенная версия остаётся исследовательским кандидатом. Для допуска к торговле требуется накопить не менее 100 завершённых наблюдений и повторно проверить устойчивость результата.</p>
</div>

</body>
</html>"""

def render_edge_stability_page_ru_v1(payload: dict | None = None) -> str:
    import html
    import os
    import re
    import subprocess

    def esc(v):
        return html.escape("" if v is None else str(v))

    def status_ru(v):
        mapping = {
            "EDGE_STABLE_REAL_PF": "🟢 Устойчивое торговое преимущество",
            "EDGE_MIXED_REAL_PF": "⚪ Смешанный результат",
            "EDGE_BROKEN_REAL_PF": "🔴 Преимущество не подтверждено",
            "EDGE_DECAYING_REAL_PF": "🟡 Преимущество ослабевает",
            "EDGE_STABLE": "🟢 Устойчивое торговое преимущество",
            "EDGE_WEAK_POSITIVE": "🟡 Слабое положительное преимущество",
            "EDGE_BROKEN": "🔴 Преимущество не подтверждено",
            "EDGE_MIXED": "⚪ Смешанный результат",
            "INSUFFICIENT_DATA": "⚪ Недостаточно данных",
        }
        return mapping.get(str(v), esc(v))

    env = os.environ.copy()
    env.setdefault("RUNTIME_ALLOW_TRADING", "0")
    env.setdefault("EXECUTION_ENABLED", "0")
    env.setdefault("REAL_TRADING_ENABLED", "0")

    proc = subprocess.run(
        [
            "/opt/finam-core/venv/bin/python3",
            "src/scripts/research/build_edge_stability_report_v1_1_real_pf.py",
        ],
        cwd="/opt/finam-core",
        env=env,
        text=True,
        capture_output=True,
        timeout=60,
    )

    raw = (proc.stdout or "") + "\n" + (proc.stderr or "")

    rows = []
    current = None

    for line in raw.splitlines():
        if line.startswith("CANDIDATE "):
            m = re.search(r"selection=([^ ]+) filter=([^ ]+)", line)
            if m:
                current = {
                    "selection": m.group(1),
                    "filter": m.group(2),
                }

        elif line.startswith("WINDOW=ALL ") and current:
            d = dict(re.findall(r"([a-zA-Z_]+)=([^ ]+)", line))
            current.update(d)

        elif line.startswith("EDGE_VERDICT ") and current:
            m = re.search(r"verdict=([^ ]+)", line)
            current["verdict"] = m.group(1) if m else ""
            rows.append(current)
            current = None

    def to_float(x):
        try:
            return float(x or 0)
        except Exception:
            return 0.0

    rows = sorted(
        rows,
        key=lambda r: (
            to_float(r.get("real_pf")),
            int(r.get("completed") or 0),
            to_float(r.get("expectancy")),
        ),
        reverse=True,
    )

    leader = rows[0] if rows else {}

    table_rows = ""
    for r in rows:
        table_rows += f"""
        <tr>
          <td>{esc(r.get('selection'))}</td>
          <td>{esc(r.get('filter'))}</td>
          <td>{esc(r.get('completed'))}</td>
          <td>{esc(r.get('success'))}</td>
          <td>{esc(r.get('failure'))}</td>
          <td>{esc(r.get('winrate'))}</td>
          <td>{esc(fmt_dashboard_number(r.get('real_pf')))}</td>
          <td>{esc(fmt_dashboard_number(r.get('expectancy')))}</td>
          <td>{status_ru(r.get('verdict'))}</td>
        </tr>
        """

    if not table_rows:
        table_rows = "<tr><td colspan='9'>Нет данных для отчёта устойчивости.</td></tr>"

    leader_html = f"""
    <div class="card">
      <h2>🏆 Лучший результат исследования</h2>
      <div><b>Селекция:</b> {esc(leader.get('selection', 'нет данных'))}</div>
      <div><b>Фильтр:</b> {esc(leader.get('filter', 'нет данных'))}</div>
      <div><b>Завершено наблюдений:</b> {esc(leader.get('completed', 0))}</div>
      <div><b>Доля успешных сигналов:</b> {esc(leader.get('winrate', 0))}</div>
      <div><b>Реальный коэффициент прибыли:</b> {esc(leader.get('real_pf', 0))}</div>
      <div><b>Математическое ожидание:</b> {esc(leader.get('expectancy', 0))}</div>
      <div><b>Статус:</b> {status_ru(leader.get('verdict', ''))}</div>
    </div>
    """

    conclusion = """
    <div class="card">
      <h2>Выводы</h2>
      <p><b>Основной кандидат:</b> BOTTOM3 / REVERSAL_UP_CLOSE.</p>
      <p><b>Резервный кандидат:</b> BOTTOM1 / REVERSAL_UP_CLOSE, но выборка меньше.</p>
      <p><b>BOTTOM3 / COMPRESSION_RANGE</b> показывает слабое положительное преимущество после пересчёта реального коэффициента прибыли.</p>
      <p><b>Реальная торговля:</b> отключена. Для допуска нужны более длинная статистика, контроль комиссий, проскальзывания и проверка устойчивости вне текущего короткого периода.</p>
    </div>
    """

    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Устойчивость торгового преимущества</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 14px; background: #fafafa; color: #111; }}
.card {{ background: white; border: 1px solid #ddd; border-radius: 12px; padding: 12px; margin: 10px 0; }}
.nav a {{ display: inline-block; margin: 4px 8px 8px 0; }}
table {{ border-collapse: collapse; width: 100%; font-size: 13px; background: white; }}
th, td {{ border: 1px solid #ddd; padding: 6px; text-align: left; }}
th {{ background: #f3f3f3; }}
</style>
</head>
<body>
{dashboard_nav_ru("Устойчивость преимущества")}

<h1>Устойчивость торгового преимущества</h1>

{leader_html}

<div class="card">
  <h2>Рейтинг кандидатов</h2>
  <table>
    <tr>
      <th>Селекция</th>
      <th>Фильтр</th>
      <th>Завершено</th>
      <th>Успешно</th>
      <th>Неуспешно</th>
      <th>Доля успешных</th>
      <th>Реальный PF</th>
      <th>Матожидание</th>
      <th>Статус</th>
    </tr>
    {table_rows}
  </table>
</div>

{conclusion}

</body>
</html>"""

def render_brent_rollover_breakout_readiness_page(payload: dict | None = None) -> str:
    import html
    import os
    import subprocess

    def esc(x):
        return html.escape("" if x is None else str(x))

    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    env["RUNTIME_ALLOW_TRADING"] = "0"
    env["EXECUTION_ENABLED"] = "0"
    env["REAL_TRADING_ENABLED"] = "0"

    try:
        p = subprocess.run(
            ["/opt/finam-core/venv/bin/python3", "src/scripts/research/build_brent_rollover_edge_v1.py"],
            cwd="/opt/finam-core",
            env=env,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
        raw = p.stdout if p.returncode == 0 else (p.stdout + "\n" + p.stderr)
    except Exception as exc:
        raw = f"ошибка_dashboard={type(exc).__name__}:{exc}"

    rows = []
    verdict = "UNKNOWN"

    for line in raw.splitlines():
        if line.startswith("BRENT_ROLLOVER_ROW "):
            d = {}
            for part in line.split()[1:]:
                if "=" in part:
                    k, v = part.split("=", 1)
                    d[k] = v
            rows.append(d)
        elif "rollover_verdict=" in line:
            verdict = line.split("=", 1)[1]

    row_html = ""
    for r in rows:
        row_html += (
            "<tr>"
            f"<td>{esc(r.get('symbol'))}</td>"
            f"<td>{esc(r.get('observations'))}</td>"
            f"<td>{esc(r.get('wins'))}</td>"
            f"<td>{esc(r.get('losses'))}</td>"
            f"<td>{esc(r.get('winrate'))}</td>"
            f"<td>{esc(r.get('avg_return_pct'))}</td>"
            f"<td><b>{esc(r.get('profit_factor'))}</b></td>"
            "</tr>"
        )

    if verdict == "UNKNOWN" and "rollover_verdict=" in raw:
        verdict = raw.split("rollover_verdict=", 1)[1].split()[0]

    if verdict == "UNKNOWN" and "BRENT_ROLLOVER_ROW" in raw:
        verdict = "ДАННЫЕ_ЕСТЬ_ВЕРДИКТ_НЕ_РАСПОЗНАН"

    if not row_html:
        row_html = "<tr><td colspan='7'>Нет данных</td></tr>"

    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="3600">
<title>Переносимость Brent Готовность к пробою</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 16px; background: #fafafa; color: #111; }}
.card {{ background: white; border: 1px solid #ddd; border-radius: 12px; padding: 12px; margin: 10px 0; }}
table {{ border-collapse: collapse; width: 100%; font-size: 13px; }}
th, td {{ border: 1px solid #ddd; padding: 6px; text-align: left; }}
th {{ background: #f3f3f3; }}
.nav a {{ display: inline-block; margin: 4px 8px 8px 0; }}
.mono {{ white-space: pre-wrap; font-family: monospace; font-size: 12px; }}
</style>
</head>
<body>
<div class="nav">
<a href="/mobile">Главная</a>
<a href="/rs-bottom-forward">RS: форвардная проверка</a>
<a href="/brent-rollover-edge">Переносимость Brent</a>
<a href="/api/current">API</a>
</div>

<h1>Переносимость Brent Готовность к пробою</h1>

<div class="card">
  <div><b>Паттерн:</b> BOTTOM1 + COMPRESSION_RANGE + 240m</div>
  <div><b>Вердикт:</b> {esc(verdict)}</div>
  <div><b>Автообновление:</b> 1 раз в час</div>
</div>

<div class="card">
<table>
<tr>
<th>Контракт</th>
<th>Наблюдений</th>
<th>Успех</th>
<th>Ошибка</th>
<th>Winrate</th>
<th>Avg return %</th>
<th>PF</th>
</tr>
{row_html}
</table>
</div>

<div class="card">
<div><b>Статус:</b> данные рассчитаны автоматически. Сервисный JSON доступен только через /api/current.</div>
</div>

</body>
</html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path = urlparse(self.path).path

        page_routes = {
            "/": "summary",
            "/current": "summary",
            "/current/": "summary",
            "/summary": "summary",
            "/summary/": "summary",
            "/history": "history",
            "/history/": "history",
            "/blockers": "blockers",
            "/blockers/": "blockers",
            "/ready": "ready",
            "/ready/": "ready",
            "/delivery": "delivery",
            "/delivery/": "delivery",
            "/rows": "rows",
            "/rows/": "rows",
            "/follow": "follow",
            "/follow/": "follow",
            "/edge": "edge",
            "/edge/": "edge",
            "/compression": "compression",
            "/compression/": "compression",
            "/compression-history": "compression_history",
            "/compression-history/": "compression_history",
            "/journal": "journal",
            "/journal/": "journal",
        }

        try:
            payload = collect_payload()

            if path in {"/rs-bottom-paper", "/rs-bottom-paper/"}:
                body = render_rs_bottom_paper_page(payload).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return



            if path in {"/rs-breakout-confirmation", "/rs-breakout-confirmation/"}:
                body = render_rs_breakout_confirmation_page(None).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return


            if path in {"/equities", "/equities/"}:
                body = render_equities_dashboard_v1(payload).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

            if path in {"/rs-bottom-clean", "/rs-bottom-clean/"}:
                body = render_rs_bottom_clean_subset_dashboard_v1(payload).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

            if path in {"/edge-stability", "/edge-stability/"}:
                body = render_edge_stability_page_ru_v1(payload).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

            if path in {"/leaderboard", "/leaderboard/"}:
                body = render_rs_bottom_forward_leaderboard_page(payload).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

            if path in {"/rs-bottom-forward", "/rs-bottom-forward/"}:
                body = render_rs_bottom_forward_page(payload).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return



            if path in {"/", ""}:
                self.send_response(302)
                self.send_header("Location", "/mobile")
                self.end_headers()
                return

            if path in {"/mobile", "/mobile/"}:
                body = render_mobile_research_summary_page(payload).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return


            if path in {"/brent-rollover-edge", "/brent-rollover-edge/"}:
                body = render_brent_rollover_breakout_readiness_page(payload).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return


            if path in {"/brent-rollover-edge", "/brent-rollover-edge/"}:
                body = render_brent_rollover_breakout_readiness_page(payload).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

            if path in {"/api/current", "/api/current/"}:
                body = json.dumps(payload, ensure_ascii=False, indent=2, default=str).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(body)
                self.close_connection = True
                return

            if path in page_routes:
                body = render_page(payload, page_routes[path]).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(body)
                self.close_connection = True
                return

            body = "страница не найдена".encode("utf-8")
            self.send_response(404)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(body)
            self.close_connection = True

        except Exception as exc:
            body = f"ошибка_dashboard={type(exc).__name__}:{exc}".encode("utf-8")
            self.send_response(500)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(body)
            self.close_connection = True

    def log_message(self, fmt: str, *args: object) -> None:
        print("MULTI_ASSET_DASHBOARD_HTTP " + fmt % args, flush=True)


def main() -> int:
    print("=== MULTI ASSET BREAKOUT DASHBOARD V1 ===", flush=True)
    print(f"port={PORT}", flush=True)
    print("mode=read_only", flush=True)
    print("execution_enabled=0", flush=True)
    print("real_trading_enabled=0", flush=True)
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())



