#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path("/opt/finam-core")
UNIT = "finam-multi-asset-breakout-telegram.service"
TIMER = "finam-multi-asset-breakout-telegram.timer"
SINCE = os.getenv("SINCE", "2026-06-19 13:39:00")


def run(cmd: list[str]) -> tuple[int, str]:
    result = subprocess.run(
        cmd,
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=False,
    )
    return result.returncode, (result.stdout or "") + "\n" + (result.stderr or "")


def count(pattern: str, text: str) -> int:
    return sum(1 for line in text.splitlines() if pattern in line)


def last_value(key: str, text: str) -> str:
    value = "UNKNOWN"
    pattern = re.compile(rf"{re.escape(key)}=([^ \n]+)")
    for line in text.splitlines():
        m = pattern.search(line)
        if m:
            value = m.group(1)
    return value


def main() -> int:
    print("=== MULTI ASSET BREAKOUT TELEGRAM SYSTEMD RUNTIME VALIDATION V1 ===")
    print("mode=read_only")
    print(f"runtime_allow={os.getenv('RUNTIME_ALLOW_TRADING', '0')}")
    print(f"execution_enabled={os.getenv('EXECUTION_ENABLED', '0')}")
    print(f"real_trading_enabled={os.getenv('REAL_TRADING_ENABLED', '0')}")
    print("db_update=0")
    print("telegram_real_send=0")
    print(f"unit={UNIT}")
    print(f"timer={TIMER}")
    print(f"since={SINCE}")
    print(f"checked_at_utc={datetime.now(timezone.utc).isoformat()}")

    timer_code, timer_output = run(["systemctl", "is-active", TIMER])
    enabled_code, enabled_output = run(["systemctl", "is-enabled", TIMER])
    service_code, service_status = run(["systemctl", "status", UNIT, "--no-pager"])
    timers_code, timers_output = run(["systemctl", "list-timers", "--all"])

    journal_code, journal_output = run([
        "journalctl",
        "-u",
        UNIT,
        "--since",
        SINCE,
        "--no-pager",
    ])

    timer_active = int(timer_code == 0 and timer_output.strip() == "active")
    timer_enabled = int(enabled_code == 0 and enabled_output.strip() in {"enabled", "static"})
    service_success = int("status=0/SUCCESS" in service_status or "Deactivated successfully" in service_status)
    timer_listed = int(TIMER in timers_output)

    execution_bad = count("execution_enabled=1", journal_output)
    real_bad = count("real_trading_enabled=1", journal_output)
    tracebacks = count("Traceback", journal_output)
    errors = count("ERROR", journal_output)

    verdict_lines = count("VERDICT=MULTI_ASSET_BREAKOUT_TELEGRAM_SENDER_", journal_output)
    dry_run_lines = count("telegram_dry_run=1", journal_output)
    sent_zero_lines = count("telegram_sent=0", journal_output)

    last_runtime_allow = last_value("runtime_allow", journal_output)
    last_execution_enabled = last_value("execution_enabled", journal_output)
    last_real_trading_enabled = last_value("real_trading_enabled", journal_output)
    last_telegram_dry_run = last_value("telegram_dry_run", journal_output)
    last_telegram_sent = last_value("telegram_sent", journal_output)

    print()
    print("MULTI_ASSET_BREAKOUT_TELEGRAM_SYSTEMD_RUNTIME_ROWS")
    print(f"timer_active={timer_active}")
    print(f"timer_enabled={timer_enabled}")
    print(f"timer_listed={timer_listed}")
    print(f"service_success={service_success}")
    print(f"journal_available={int(journal_code == 0)}")
    print(f"sender_verdict_lines={verdict_lines}")
    print(f"telegram_dry_run_lines={dry_run_lines}")
    print(f"telegram_sent_zero_lines={sent_zero_lines}")
    print(f"execution_bad_lines={execution_bad}")
    print(f"real_trading_bad_lines={real_bad}")
    print(f"tracebacks={tracebacks}")
    print(f"errors={errors}")

    print()
    print("MULTI_ASSET_BREAKOUT_TELEGRAM_SYSTEMD_LAST_VALUES")
    print(f"last_runtime_allow={last_runtime_allow}")
    print(f"last_execution_enabled={last_execution_enabled}")
    print(f"last_real_trading_enabled={last_real_trading_enabled}")
    print(f"last_telegram_dry_run={last_telegram_dry_run}")
    print(f"last_telegram_sent={last_telegram_sent}")

    print()
    print("MULTI_ASSET_BREAKOUT_TELEGRAM_SYSTEMD_RUNTIME_VALIDATION_SUMMARY")
    print(f"timer_active={timer_active}")
    print(f"timer_enabled={timer_enabled}")
    print(f"timer_listed={timer_listed}")
    print(f"service_success={service_success}")
    print(f"last_execution_enabled={last_execution_enabled}")
    print(f"last_real_trading_enabled={last_real_trading_enabled}")
    print(f"last_telegram_dry_run={last_telegram_dry_run}")
    print(f"last_telegram_sent={last_telegram_sent}")
    print(f"execution_bad_lines={execution_bad}")
    print(f"real_trading_bad_lines={real_bad}")
    print(f"tracebacks={tracebacks}")
    print(f"errors={errors}")
    print("db_update=0")
    print("telegram_real_send=0")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")

    ok = (
        timer_active == 1
        and timer_enabled == 1
        and timer_listed == 1
        and verdict_lines > 0
        and last_runtime_allow == "0"
        and last_execution_enabled == "0"
        and last_real_trading_enabled == "0"
        and last_telegram_dry_run == "1"
        and last_telegram_sent == "0"
        and execution_bad == 0
        and real_bad == 0
        and tracebacks == 0
        and errors == 0
    )

    if ok:
        print("VERDICT=MULTI_ASSET_BREAKOUT_TELEGRAM_SYSTEMD_RUNTIME_VALIDATION_OK")
    else:
        print("VERDICT=MULTI_ASSET_BREAKOUT_TELEGRAM_SYSTEMD_RUNTIME_VALIDATION_REVIEW_REQUIRED")

    print("MULTI_ASSET_BREAKOUT_TELEGRAM_SYSTEMD_RUNTIME_VALIDATION_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
