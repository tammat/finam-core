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
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path("/opt/finam-core")
PORT = int(os.getenv("MULTI_ASSET_DASHBOARD_PORT", "8088"))
V2_SCRIPT = "src/scripts/research/build_multi_asset_breakout_watch_v2.py"
PLAN_SCRIPT = "src/scripts/research/build_multi_asset_breakout_telegram_notify_plan_v1.py"
JOURNAL_UNIT = "finam-multi-asset-breakout-telegram.service"


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
        f"<td>{esc(r.get('last_seen', ''))}</td>"
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
<div>первый снимок: <span class="mono">{esc(history.get("first_snapshot", "NONE"))}</span></div>
<div>последний снимок: <span class="mono">{esc(history.get("last_snapshot", "NONE"))}</span></div>
<h3>Причины блокировки за день</h3>
<div>NO_BREAKOUT: {esc(history.get("blockers", {}).get("NO_BREAKOUT", 0))}</div>
<div>ATR_TOO_LOW: {esc(history.get("blockers", {}).get("ATR_TOO_LOW", 0))}</div>
<div>VOLUME_TOO_LOW: {esc(history.get("blockers", {}).get("VOLUME_TOO_LOW", 0))}</div>
<div>NO_ENOUGH_BARS: {esc(history.get("blockers", {}).get("NO_ENOUGH_BARS", 0))}</div>
<h3>Статистика по инструментам</h3>
<table>
<tr>
<th>Инструмент</th><th>Класс</th><th>ТФ</th><th>Роль</th><th>Наблюдений</th><th>Ready</th>
<th>No breakout</th><th>ATR blocked</th><th>Volume blocked</th><th>Последнее наблюдение</th>
</tr>
{history_symbol_rows}
</table>
</div>

<div class="card">
<h2 id="blockers">Причины блокировки</h2>
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


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path = urlparse(self.path).path

        try:
            payload = collect_payload()

            if path in {"/api/current", "/api/current/"}:
                body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)
                return

            if path in {"/", "/current", "/current/"}:
                body = render_html(payload).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(body)
                return

            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"not found")

        except Exception as exc:
            body = f"ошибка_dashboard={type(exc).__name__}:{exc}".encode("utf-8")
            self.send_response(500)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(body)

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
