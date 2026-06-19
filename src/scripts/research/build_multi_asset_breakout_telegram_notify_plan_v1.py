#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path("/opt/finam-core")
V2_SCRIPT = "src/scripts/research/build_multi_asset_breakout_watch_v2.py"


def run_v2() -> tuple[int, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    env["FUTURES_PREFIXES"] = env.get("FUTURES_PREFIXES", "BR,NG,GD")

    result = subprocess.run(
        [sys.executable, V2_SCRIPT],
        cwd=str(ROOT),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    return result.returncode, (result.stdout or "") + "\n" + (result.stderr or "")


def parse_key(output: str, key: str) -> str:
    for line in output.splitlines():
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1].strip()
    return "UNKNOWN"


def parse_ready_rows(output: str) -> list[str]:
    rows: list[str] = []
    for line in output.splitlines():
        if line.startswith("MULTI_ASSET_BREAKOUT_WATCH_V2_ROW ") and "status=BREAKOUT_READY" in line:
            rows.append(line)
    return rows


def extract_field(row: str, name: str) -> str:
    match = re.search(rf"{name}=([^ ]+)", row)
    return match.group(1) if match else "UNKNOWN"


def main() -> int:
    print("=== MULTI ASSET BREAKOUT TELEGRAM NOTIFY PLAN V1 ===")
    print("mode=read_only")
    print(f"runtime_allow={os.getenv('RUNTIME_ALLOW_TRADING', '0')}")
    print(f"execution_enabled={os.getenv('EXECUTION_ENABLED', '0')}")
    print(f"real_trading_enabled={os.getenv('REAL_TRADING_ENABLED', '0')}")
    print("db_update=0")
    print("telegram_send=0")
    print("telegram_mode=plan_only")
    print(f"futures_prefixes={os.getenv('FUTURES_PREFIXES', 'BR,NG,GD')}")

    code, output = run_v2()
    v2_ok = int(code == 0 and "MULTI_ASSET_BREAKOUT_WATCH_V2_OK" in output)

    breakout_ready_raw = parse_key(output, "breakout_ready")
    breakout_ready = int(breakout_ready_raw) if breakout_ready_raw.isdigit() else 0
    ready_rows = parse_ready_rows(output)

    print()
    print("MULTI_ASSET_BREAKOUT_TELEGRAM_SOURCE_ROWS")
    print(f"v2_ok={v2_ok}")
    print(f"v2_universe_total={parse_key(output, 'universe_total')}")
    print(f"v2_rows_total={parse_key(output, 'rows_total')}")
    print(f"v2_equity_rows={parse_key(output, 'equity_rows')}")
    print(f"v2_futures_rows={parse_key(output, 'futures_rows')}")
    print(f"v2_breakout_ready={breakout_ready}")
    print(f"v2_verdict={parse_key(output, 'VERDICT')}")

    print()
    print("MULTI_ASSET_BREAKOUT_TELEGRAM_READY_ROWS")

    if not ready_rows:
        print("MULTI_ASSET_BREAKOUT_TELEGRAM_READY_ROW status=NONE")

    for row in ready_rows:
        symbol = extract_field(row, "symbol")
        asset_class = extract_field(row, "asset_class")
        timeframe = extract_field(row, "timeframe")
        role = extract_field(row, "role")
        close = extract_field(row, "close")
        prev_high = extract_field(row, "prev_high")
        atr_pct = extract_field(row, "atr_pct")
        volume_ratio = extract_field(row, "volume_ratio")

        print(
            "MULTI_ASSET_BREAKOUT_TELEGRAM_READY_ROW "
            f"symbol={symbol} asset_class={asset_class} timeframe={timeframe} role={role} "
            f"close={close} prev_high={prev_high} atr_pct={atr_pct} volume_ratio={volume_ratio}"
        )

        print(
            "TELEGRAM_MESSAGE "
            f"🚨 BREAKOUT_READY | {symbol} | {asset_class} | {timeframe} | "
            f"role={role} | close={close} > prev_high={prev_high} | "
            f"atr_pct={atr_pct} | volume_ratio={volume_ratio} | execution=disabled"
        )

    decision = "SEND" if breakout_ready > 0 and ready_rows else "SILENT"

    print()
    print("MULTI_ASSET_BREAKOUT_TELEGRAM_NOTIFY_PLAN_SUMMARY")
    print(f"v2_ok={v2_ok}")
    print(f"breakout_ready={breakout_ready}")
    print(f"ready_rows={len(ready_rows)}")
    print(f"telegram_decision={decision}")
    print("telegram_send=0")
    print("db_update=0")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print(f"real_trading_enabled={os.getenv('REAL_TRADING_ENABLED', '0')}")
    print(f"execution_enabled={os.getenv('EXECUTION_ENABLED', '0')}")

    if not v2_ok:
        print("VERDICT=MULTI_ASSET_BREAKOUT_TELEGRAM_NOTIFY_PLAN_V2_FAILED")
    elif decision == "SEND":
        print("VERDICT=MULTI_ASSET_BREAKOUT_TELEGRAM_NOTIFY_PLAN_SEND_READY")
    else:
        print("VERDICT=MULTI_ASSET_BREAKOUT_TELEGRAM_NOTIFY_PLAN_SILENT")

    print("MULTI_ASSET_BREAKOUT_TELEGRAM_NOTIFY_PLAN_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
