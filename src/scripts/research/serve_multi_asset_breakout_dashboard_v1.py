#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import os
import re
import subprocess
import psycopg
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



def load_edge_scorecard_v1() -> dict:
    # Загружаем edge scorecard через отдельный read-only builder.
    import json
    import subprocess
    import sys

    cmd = [
        sys.executable,
        "src/scripts/research/build_multi_asset_breakout_edge_scorecard_8_equities_v1.py",
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
    from psycopg.rows import dict_row

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
        "edge_scorecard": load_edge_scorecard_v1(),
        "compression_expansion": load_compression_expansion_v1(),
        "compression_history": load_compression_history_v1(),
        "db_update": 0,
        "execution_changes_required": 0,
        "runtime_changes_required": 0,
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
<a href="/api/current">API JSON</a>
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
<th>Горизонт, мин</th><th>Строк</th><th>Успех</th><th>Неуспех</th><th>Ожидание</th><th>Средняя доходность</th>
</tr>
{follow_horizon_rows}
</table>

<h3>По инструментам</h3>
<table>
<tr>
<th>Инструмент</th><th>Класс</th><th>ТФ</th><th>Роль</th><th>Строк</th><th>Успех</th><th>Неуспех</th><th>Ожидание</th><th>Средняя доходность</th><th>Последний ready, МСК</th>
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

</body>
</html>"""


def render_page(payload: dict, page: str) -> str:
    def esc(x: object) -> str:
        return html.escape(str(x))

    summary = payload.get("summary", {})
    history = payload.get("history_daily", {})
    follow = payload.get("follow_through", {})
    blockers = payload.get("blocker_counts", {})
    ready_rows = payload.get("ready_rows", [])
    rows = payload.get("rows", [])
    journal_lines = payload.get("journal_lines", [])
    delivery = payload.get("ready_delivery", {})
    edge_scorecard = payload.get("edge_scorecard", {})
    compression_expansion = payload.get("compression_expansion", {})
    compression_history = payload.get("compression_history", {})
    edge = payload.get("edge_scorecard", {})

    menu = """
<nav class="menu">
<a href="/summary">Сводка</a>
<a href="/history">История за день</a>
<a href="/blockers">Блокировки</a>
<a href="/ready">Готовые сигналы</a>
<a href="/delivery">Уведомления</a>
<a href="/rows">Текущая таблица</a>
<a href="/follow">Follow-through</a>
<a href="/edge">Edge</a>
<a href="/compression">Compression</a>
<a href="/compression-history">Compression History</a>
<a href="/journal">Журнал Telegram</a>
<a href="/api/current">API JSON</a>
</nav>
"""

    style = """
<style>
body { font-family: Arial, sans-serif; margin: 24px; background: #111; color: #eee; }
h1, h2, h3 { color: #fff; }
.card { background: #1b1b1b; padding: 16px; margin-bottom: 16px; border-radius: 8px; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th, td { border-bottom: 1px solid #333; padding: 6px; text-align: left; }
th { background: #222; }
.mono { font-family: monospace; font-size: 12px; }
.menu { background: #1b1b1b; padding: 10px; margin-bottom: 16px; border-radius: 8px; }
.menu a { color: #7CFC98; margin-right: 16px; text-decoration: none; font-weight: bold; }
.good { color: #7CFC98; }
.bad { color: #ff7777; }
</style>
"""

    header = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Finam Core — наблюдение пробоев</title>
{style}
</head>
<body>
<h1>Наблюдение качества сигналов пробоя V1</h1>
{menu}
<div class="card">
<div>проверено МСК: <span class="mono">{format_msk_time(payload.get("checked_at_msk", "UNKNOWN"))}</span></div>
<div>исполнение: <span class="good">{esc(payload.get("execution_enabled", "0"))}</span></div>
<div>реальные сделки: <span class="good">{esc(payload.get("real_trading_enabled", "0"))}</span></div>
<div>Telegram dry-run: <span class="good">{esc(payload.get("telegram_dry_run", "1"))}</span></div>
</div>
"""

    footer = "</body></html>"

    if page == "summary":
        body = f"""
<div class="card">
<h2>Сводка</h2>
<div>инструментов во вселенной: {esc(summary.get("universe_total", "UNKNOWN"))}</div>
<div>строк наблюдения: {esc(summary.get("rows_total", "UNKNOWN"))}</div>
<div>акции: {esc(summary.get("equity_rows", "UNKNOWN"))}</div>
<div>фьючерсы: {esc(summary.get("futures_rows", "UNKNOWN"))}</div>
<div>готовые пробои: <b>{esc(summary.get("breakout_ready", "UNKNOWN"))}</b></div>
<div>решение Telegram: <b>{esc(summary.get("telegram_decision", "UNKNOWN"))}</b></div>
<div>вердикт V2: <span class="mono">{esc(summary.get("v2_verdict", "UNKNOWN"))}</span></div>
<div>вердикт Telegram-plan: <span class="mono">{esc(summary.get("plan_verdict", "UNKNOWN"))}</span></div>
</div>
"""
    elif page == "history":
        symbols = history.get("symbols", [])
        trs = "\n".join(
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
            for r in symbols
        ) or "<tr><td colspan='10'>История за сегодня пока пуста</td></tr>"

        body = f"""
<div class="card">
<h2>История за день</h2>
<div>снимков сегодня: <b>{esc(history.get("snapshots_today", 0))}</b></div>
<div>строк наблюдения сегодня: <b>{esc(history.get("rows_today", 0))}</b></div>
<div>BREAKOUT_READY сегодня: <b>{esc(history.get("ready_today", 0))}</b></div>
<div>первый снимок: <span class="mono">{format_msk_time(history.get("first_snapshot", "NONE"))}</span></div>
<div>последний снимок: <span class="mono">{format_msk_time(history.get("last_snapshot", "NONE"))}</span></div>
<h3>Статистика по инструментам</h3>
<table>
<tr><th>Инструмент</th><th>Класс</th><th>ТФ</th><th>Роль</th><th>Наблюдений</th><th>Ready</th><th>No breakout</th><th>ATR blocked</th><th>Volume blocked</th><th>Последнее наблюдение, МСК</th></tr>
{trs}
</table>
</div>
"""
    elif page == "blockers":
        day = history.get("blockers", {})
        body = f"""
<div class="card">
<h2>Причины блокировки — текущий срез</h2>
<div>NO_BREAKOUT: {esc(blockers.get("no_breakout", 0))}</div>
<div>ATR_TOO_LOW: {esc(blockers.get("atr_too_low", 0))}</div>
<div>VOLUME_TOO_LOW: {esc(blockers.get("volume_too_low", 0))}</div>
<div>NO_ENOUGH_BARS: {esc(blockers.get("no_enough_bars", 0))}</div>
</div>
<div class="card">
<h2>Причины блокировки — за день</h2>
<div>NO_BREAKOUT: {esc(day.get("NO_BREAKOUT", 0))}</div>
<div>ATR_TOO_LOW: {esc(day.get("ATR_TOO_LOW", 0))}</div>
<div>VOLUME_TOO_LOW: {esc(day.get("VOLUME_TOO_LOW", 0))}</div>
<div>NO_ENOUGH_BARS: {esc(day.get("NO_ENOUGH_BARS", 0))}</div>
</div>
"""
    elif page == "ready":
        lis = "\n".join(
            f"<li>{esc(r.get('symbol'))} {esc(r.get('timeframe'))} {esc(r.get('role'))} close={esc(r.get('close'))} status={esc(r.get('status'))}</li>"
            for r in ready_rows
        ) or "<li>Готовых сигналов нет</li>"
        body = f"""
<div class="card">
<h2>Готовые сигналы BREAKOUT_READY</h2>
<ul>{lis}</ul>
</div>
"""

    elif page == "delivery":
        delivery_rows = "\n".join(
            "<tr>"
            f"<td>{esc(r.get('ready_row_id'))}</td>"
            f"<td>{esc(r.get('symbol'))}</td>"
            f"<td>{esc(r.get('timeframe'))}</td>"
            f"<td>{esc(r.get('role'))}</td>"
            f"<td>{esc(r.get('delivery_status'))}</td>"
            f"<td>{esc(r.get('dry_run'))}</td>"
            f"<td>{esc(r.get('delivery_reason'))}</td>"
            f"<td>{esc(r.get('close'))}</td>"
            f"<td>{esc(r.get('prev_high'))}</td>"
            f"<td>{format_msk_time(r.get('ready_created_at'))}</td>"
            f"<td>{format_msk_time(r.get('delivered_at'))}</td>"
            "</tr>"
            for r in delivery.get("rows", [])
        ) or "<tr><td colspan='11'>Обработанных ready-сигналов пока нет</td></tr>"

        body = f"""
<div class="card">
<h2>Уведомления по готовым сигналам</h2>
<div>Готовых сигналов всего: <b>{esc(delivery.get("ready_total", 0))}</b></div>
<div>Обработано уведомлений: <b>{esc(delivery.get("delivery_total", 0))}</b></div>
<div>Dry-run уведомлений: <b>{esc(delivery.get("dry_run_total", 0))}</b></div>
<div>Новых необработанных сигналов: <b>{esc(delivery.get("undelivered_ready", 0))}</b></div>
<h3>Последние обработанные сигналы</h3>
<table>
<tr>
<th>ready_id</th><th>Инструмент</th><th>ТФ</th><th>Роль</th><th>Статус уведомления</th><th>Dry-run</th>
<th>Комментарий</th><th>Close</th><th>Prev high</th><th>Время сигнала, МСК</th><th>Время обработки, МСК</th>
</tr>
{delivery_rows}
</table>
</div>
"""

    elif page == "rows":
        trs = "\n".join(
            "<tr>"
            f"<td>{esc(r.get('symbol'))}</td>"
            f"<td>{esc(r.get('asset_class'))}</td>"
            f"<td>{esc(r.get('timeframe'))}</td>"
            f"<td>{esc(r.get('role'))}</td>"
            f"<td>{esc(r.get('close'))}</td>"
            f"<td>{esc(r.get('prev_high'))}</td>"
            f"<td>{esc(r.get('breakout_ok'))}</td>"
            f"<td>{esc(r.get('atr_ok'))}</td>"
            f"<td>{esc(r.get('volume_ok'))}</td>"
            f"<td>{esc(r.get('status'))}</td>"
            "</tr>"
            for r in rows
        )
        body = f"""
<div class="card">
<h2>Текущая таблица наблюдения</h2>
<table>
<tr><th>Инструмент</th><th>Класс</th><th>ТФ</th><th>Роль</th><th>Закрытие</th><th>Пред. максимум</th><th>Пробой</th><th>ATR</th><th>Объём</th><th>Статус</th></tr>
{trs}
</table>
</div>
"""
    elif page == "follow":
        horizon_rows = "\n".join(
            "<tr>"
            f"<td>{esc(r.get('horizon_min'))}</td>"
            f"<td>{esc(r.get('rows'))}</td>"
            f"<td>{esc(r.get('wins'))}</td>"
            f"<td>{esc(r.get('losses'))}</td>"
            f"<td>{esc(r.get('waiting'))}</td>"
            f"<td>{esc(r.get('avg_return_pct'))}</td>"
            "</tr>"
            for r in follow.get("horizons", [])
        ) or "<tr><td colspan='6'>Пока нет BREAKOUT_READY для оценки</td></tr>"

        symbol_rows = "\n".join(
            "<tr>"
            f"<td>{esc(r.get('symbol'))}</td>"
            f"<td>{esc(r.get('asset_class'))}</td>"
            f"<td>{esc(r.get('timeframe'))}</td>"
            f"<td>{esc(r.get('role'))}</td>"
            f"<td>{esc(r.get('rows'))}</td>"
            f"<td>{esc(r.get('wins'))}</td>"
            f"<td>{esc(r.get('losses'))}</td>"
            f"<td>{esc(r.get('waiting'))}</td>"
            f"<td>{esc(r.get('avg_return_pct'))}</td>"
            f"<td>{format_msk_time(r.get('last_ready'))}</td>"
            "</tr>"
            for r in follow.get("symbols", [])
        ) or "<tr><td colspan='10'>Пока нет сигналов для оценки</td></tr>"

        body = f"""
<div class="card">
<h2>Follow-through scorecard</h2>
<div>BREAKOUT_READY всего: <b>{esc(follow.get("ready_rows", 0))}</b></div>
<div>строк scorecard: <b>{esc(follow.get("scorecard_rows_total", 0))}</b></div>
<div>ожидают будущую цену: <b>{esc(follow.get("waiting_rows", 0))}</b></div>
<h3>Горизонты 3/5/10/15 минут</h3>
<table>
<tr><th>Горизонт, мин</th><th>Строк</th><th>Успех</th><th>Неуспех</th><th>Ожидание</th><th>Средняя доходность</th></tr>
{horizon_rows}
</table>
<h3>По инструментам</h3>
<table>
<tr><th>Инструмент</th><th>Класс</th><th>ТФ</th><th>Роль</th><th>Строк</th><th>Успех</th><th>Неуспех</th><th>Ожидание</th><th>Средняя доходность</th><th>Последний ready, МСК</th></tr>
{symbol_rows}
</table>
</div>
"""
    elif page == "edge":
        edge_rows = "\n".join(
            "<tr>"
            f"<td>{esc(r.get('symbol', ''))}</td>"
            f"<td>{esc(r.get('priority', ''))}</td>"
            f"<td>{esc(r.get('runtime_score', ''))}</td>"
            f"<td>{esc(r.get('observations', 0))}</td>"
            f"<td>{esc(r.get('close_to_breakout', 0))}</td>"
            f"<td>{esc(r.get('breakout_ready', 0))}</td>"
            f"<td>{esc(r.get('follow_rows', 0))}</td>"
            f"<td>{esc(r.get('follow_success', 0))}</td>"
            f"<td>{esc(r.get('follow_failure', 0))}</td>"
            f"<td>{esc(r.get('avg_return_pct', 0))}</td>"
            f"<td>{esc(r.get('close_rate', 0))}</td>"
            f"<td>{esc(r.get('ready_rate', 0))}</td>"
            f"<td>{esc(r.get('follow_winrate', 0))}</td>"
            f"<td><b>{esc(r.get('edge_score', 0))}</b></td>"
            f"<td>{format_msk_time(r.get('last_seen', ''))}</td>"
            "</tr>"
            for r in edge_scorecard.get("rows", [])
        ) or "<tr><td colspan='15'>Edge scorecard пока пуст</td></tr>"

        body = f"""
<div class="card">
<h2>Edge Scorecard 8 equities V1</h2>
<div>вердикт: <span class="mono">{esc(edge_scorecard.get("verdict", "UNKNOWN"))}</span></div>
<div>runtime equities: <b>{esc(edge_scorecard.get("runtime_equities", 0))}</b></div>
<div>строк scorecard: <b>{esc(edge_scorecard.get("scorecard_rows", 0))}</b></div>
<div>equities with READY: <b>{esc(edge_scorecard.get("equities_with_ready", 0))}</b></div>
<div>equities with follow-through: <b>{esc(edge_scorecard.get("equities_with_follow", 0))}</b></div>
<div>top edge symbol: <b>{esc(edge_scorecard.get("top_edge_symbol", "NONE"))}</b></div>
<div>top edge score: <b>{esc(edge_scorecard.get("top_edge_score", "NONE"))}</b></div>

<h3>Таблица edge по 8 акциям</h3>
<table>
<tr>
<th>Инструмент</th><th>Priority</th><th>Runtime score</th><th>Наблюдений</th>
<th>Close to breakout</th><th>READY</th><th>Follow rows</th>
<th>Follow success</th><th>Follow failure</th><th>Avg return %</th>
<th>Close rate</th><th>Ready rate</th><th>Follow winrate</th><th>Edge score</th><th>Последнее наблюдение, МСК</th>
</tr>
{edge_rows}
</table>
</div>
"""
    
    elif page == "compression":
        compression_rows = "\n".join(
            "<tr>"
            f"<td>{esc(r.get('symbol', ''))}</td>"
            f"<td>{esc(r.get('asset_class', ''))}</td>"
            f"<td>{esc(r.get('timeframe', ''))}</td>"
            f"<td>{esc(r.get('status', ''))}</td>"
            f"<td>{esc(r.get('compression_score', 0))}</td>"
            f"<td>{esc(r.get('expansion_score', 0))}</td>"
            f"<td>{esc(r.get('last_close', ''))}</td>"
            f"<td>{esc(r.get('range_high', ''))}</td>"
            f"<td>{esc(r.get('range_low', ''))}</td>"
            f"<td>{esc(r.get('volume_ratio', ''))}</td>"
            "</tr>"
            for r in compression_expansion.get("rows", [])
        ) or "<tr><td colspan='10'>Compression scorecard пока пуст</td></tr>"

        body = f"""
<div class="card">
<h2>Compression / Expansion Watch V1</h2>
<div>вердикт: <span class="mono">{esc(compression_expansion.get("verdict", "UNKNOWN"))}</span></div>
<div>строк: <b>{esc(compression_expansion.get("rows_total", 0))}</b></div>
<div>акции: <b>{esc(compression_expansion.get("equities_total", 0))}</b></div>
<div>фьючерсы/FX: <b>{esc(compression_expansion.get("futures_total", 0))}</b></div>
<div>индексы: <b>{esc(compression_expansion.get("indexes_total", 0))}</b></div>
<div>сжатие: <b>{esc(compression_expansion.get("compression_count", 0))}</b></div>
<div>кандидаты расширения: <b>{esc(compression_expansion.get("expansion_candidate_count", 0))}</b></div>
<div>без данных: <b>{esc(compression_expansion.get("no_bars", 0))}</b></div>

<h3>Таблица Compression / Expansion</h3>
<table>
<tr>
<th>Инструмент</th><th>Класс</th><th>ТФ</th><th>Статус</th>
<th>Compression</th><th>Expansion</th><th>Close</th>
<th>Range high</th><th>Range low</th><th>Volume ratio</th>
</tr>
{compression_rows}
</table>
</div>
"""

    
    elif page == "compression_history":
        snapshot_rows = "\n".join(
            "<tr>"
            f"<td>{esc(r.get('id', ''))}</td>"
            f"<td>{format_msk_time(r.get('created_at', ''))}</td>"
            f"<td>{esc(r.get('rows_total', 0))}</td>"
            f"<td>{esc(r.get('equities_total', 0))}</td>"
            f"<td>{esc(r.get('futures_total', 0))}</td>"
            f"<td>{esc(r.get('indexes_total', 0))}</td>"
            f"<td>{esc(r.get('compression_count', 0))}</td>"
            f"<td>{esc(r.get('expansion_candidate_count', 0))}</td>"
            f"<td>{esc(r.get('no_setup', 0))}</td>"
            f"<td>{esc(r.get('verdict', ''))}</td>"
            "</tr>"
            for r in compression_history.get("snapshot_rows", [])
        ) or "<tr><td colspan='10'>История snapshot пока пуста</td></tr>"

        top_rows = "\n".join(
            "<tr>"
            f"<td>{esc(r.get('symbol', ''))}</td>"
            f"<td>{esc(r.get('asset_class', ''))}</td>"
            f"<td>{esc(r.get('compression_hits', 0))}</td>"
            f"<td>{esc(r.get('expansion_hits', 0))}</td>"
            f"<td>{esc(r.get('no_setup_hits', 0))}</td>"
            f"<td>{format_msk_time(r.get('last_seen', ''))}</td>"
            "</tr>"
            for r in compression_history.get("top_symbols", [])
        ) or "<tr><td colspan='6'>История инструментов пока пуста</td></tr>"

        body = f"""
<div class="card">
<h2>Compression / Expansion History V1</h2>
<div>вердикт: <span class="mono">{esc(compression_history.get("verdict", "UNKNOWN"))}</span></div>
<div>snapshots: <b>{esc(compression_history.get("snapshots", 0))}</b></div>
<div>history rows: <b>{esc(compression_history.get("rows", 0))}</b></div>
<div>compression rows: <b>{esc(compression_history.get("compression_rows", 0))}</b></div>
<div>expansion rows: <b>{esc(compression_history.get("expansion_rows", 0))}</b></div>
<div>no setup rows: <b>{esc(compression_history.get("no_setup_rows", 0))}</b></div>
<div>last snapshot, МСК: <b>{format_msk_time(compression_history.get("last_snapshot", ""))}</b></div>

<h3>Последние snapshot</h3>
<table>
<tr>
<th>ID</th><th>Время, МСК</th><th>Rows</th><th>Equities</th><th>Futures/FX</th><th>Indexes</th>
<th>Compression</th><th>Expansion</th><th>No setup</th><th>Verdict</th>
</tr>
{snapshot_rows}
</table>

<h3>Топ инструментов по истории</h3>
<table>
<tr>
<th>Инструмент</th><th>Класс</th><th>Compression hits</th><th>Expansion hits</th><th>No setup hits</th><th>Last seen, МСК</th>
</tr>
{top_rows}
</table>
</div>
"""

    elif page == "journal":
        journal = "<br>".join(esc(x) for x in journal_lines[-80:])
        body = f"""
<div class="card">
<h2>Журнал Telegram sender</h2>
<div class="mono">{journal}</div>
</div>
"""
    else:
        body = """
<div class="card">
<h2>Страница не найдена</h2>
</div>
"""

    return header + body + footer


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
