#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import os
import re
import subprocess
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


def collect_payload() -> dict:
    v2_code, v2_output = run_cmd(["python3", V2_SCRIPT])
    plan_code, plan_output = run_cmd(["python3", PLAN_SCRIPT])

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
        "db_update": 0,
        "execution_changes_required": 0,
        "runtime_changes_required": 0,
    }


def render_html(payload: dict) -> str:
    summary = payload["summary"]
    rows = payload["rows"]
    ready = payload["ready_rows"]
    blockers = payload["blocker_counts"]

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
    ) or "<li>Нет BREAKOUT_READY</li>"

    journal_html = "<br>".join(esc(x) for x in payload["journal_lines"][-30:])

    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Finam Core Multi-Asset Breakout Watch</title>
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
</style>
</head>
<body>
<h1>Multi-Asset Breakout Signal Quality Observation V1</h1>

<div class="card">
<div>checked_at_utc: <span class="mono">{esc(payload["checked_at_utc"])}</span></div>
<div>mode: <span class="mono">{esc(payload["mode"])}</span></div>
<div>execution_enabled: <span class="good">{esc(payload["execution_enabled"])}</span></div>
<div>real_trading_enabled: <span class="good">{esc(payload["real_trading_enabled"])}</span></div>
<div>telegram_dry_run: <span class="good">{esc(payload["telegram_dry_run"])}</span></div>
</div>

<div class="card">
<h2>Summary</h2>
<div>universe_total: {esc(summary["universe_total"])}</div>
<div>rows_total: {esc(summary["rows_total"])}</div>
<div>equity_rows: {esc(summary["equity_rows"])}</div>
<div>futures_rows: {esc(summary["futures_rows"])}</div>
<div>breakout_ready: <b>{esc(summary["breakout_ready"])}</b></div>
<div>telegram_decision: <b>{esc(summary["telegram_decision"])}</b></div>
<div>v2_verdict: <span class="mono">{esc(summary["v2_verdict"])}</span></div>
<div>plan_verdict: <span class="mono">{esc(summary["plan_verdict"])}</span></div>
</div>

<div class="card">
<h2>Blockers</h2>
<div>NO_BREAKOUT: {esc(blockers["no_breakout"])}</div>
<div>ATR_TOO_LOW: {esc(blockers["atr_too_low"])}</div>
<div>VOLUME_TOO_LOW: {esc(blockers["volume_too_low"])}</div>
<div>NO_ENOUGH_BARS: {esc(blockers["no_enough_bars"])}</div>
</div>

<div class="card">
<h2>BREAKOUT_READY</h2>
<ul>{ready_html}</ul>
</div>

<div class="card">
<h2>Watch Rows</h2>
<table>
<tr>
<th>Symbol</th><th>Class</th><th>TF</th><th>Role</th><th>Close</th><th>Prev High</th>
<th>Breakout</th><th>ATR</th><th>Volume</th><th>Status</th>
</tr>
{row_html}
</table>
</div>

<div class="card">
<h2>Telegram Sender Journal</h2>
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
            body = f"dashboard_error={type(exc).__name__}:{exc}".encode("utf-8")
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
