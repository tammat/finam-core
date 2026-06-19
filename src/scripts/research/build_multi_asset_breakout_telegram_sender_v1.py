#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

from finam_core.notifications.telegram_signal_dispatcher import TelegramSignalDispatcher
from finam_core.notifications.telegram_signal_taxonomy import TelegramSignalMessage


ROOT = Path("/opt/finam-core")
PLAN_SCRIPT = "src/scripts/research/build_multi_asset_breakout_telegram_notify_plan_v1.py"


def run_plan() -> tuple[int, str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    env["FUTURES_PREFIXES"] = env.get("FUTURES_PREFIXES", "BR,NG,GD")
    result = subprocess.run(
        ["python3", PLAN_SCRIPT],
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


def extract(row: str, key: str) -> str:
    m = re.search(rf"{key}=([^ ]+)", row)
    return m.group(1) if m else "UNKNOWN"


def ready_rows(output: str) -> list[str]:
    return [
        line for line in output.splitlines()
        if line.startswith("MULTI_ASSET_BREAKOUT_TELEGRAM_READY_ROW ")
        and "status=NONE" not in line
    ]


def main() -> int:
    print("=== MULTI ASSET BREAKOUT TELEGRAM SENDER V1 ===")
    print("mode=sender_guarded")
    print(f"runtime_allow={os.getenv('RUNTIME_ALLOW_TRADING', '0')}")
    print(f"execution_enabled={os.getenv('EXECUTION_ENABLED', '0')}")
    print(f"real_trading_enabled={os.getenv('REAL_TRADING_ENABLED', '0')}")
    print("db_update=0")

    dry_run = os.getenv("MULTI_ASSET_TELEGRAM_DRY_RUN", "1") != "0"
    print(f"telegram_dry_run={int(dry_run)}")

    code, plan_output = run_plan()
    plan_ok = int(code == 0 and "MULTI_ASSET_BREAKOUT_TELEGRAM_NOTIFY_PLAN_V1_OK" in plan_output)
    decision = parse_key(plan_output, "telegram_decision")
    rows = ready_rows(plan_output)

    print()
    print("MULTI_ASSET_BREAKOUT_TELEGRAM_SENDER_SOURCE")
    print(f"plan_ok={plan_ok}")
    print(f"telegram_decision={decision}")
    print(f"ready_rows={len(rows)}")

    sent = 0
    skipped = 0

    if not plan_ok:
        print("MULTI_ASSET_BREAKOUT_TELEGRAM_SENDER_SKIP reason=plan_failed")
        skipped += 1
    elif decision != "SEND":
        print("MULTI_ASSET_BREAKOUT_TELEGRAM_SENDER_SKIP reason=telegram_decision_not_send")
        skipped += 1
    elif not rows:
        print("MULTI_ASSET_BREAKOUT_TELEGRAM_SENDER_SKIP reason=no_ready_rows")
        skipped += 1
    else:
        for row in rows:
            symbol = extract(row, "symbol")
            asset_class = extract(row, "asset_class")
            timeframe = extract(row, "timeframe")
            close = extract(row, "close")
            prev_high = extract(row, "prev_high")
            atr_pct = extract(row, "atr_pct")
            volume_ratio = extract(row, "volume_ratio")

            msg = TelegramSignalMessage(
                channel_type="RADAR",
                symbol=symbol,
                display_name=symbol,
                direction="BREAKOUT",
                source="MULTI_ASSET_BREAKOUT_WATCH_V2",
                strategy="MULTI_ASSET_BREAKOUT_WATCH_V2",
                timeframe=timeframe,
                confidence=0.70,
                entry=float(close) if close != "UNKNOWN" else None,
                stop=None,
                take=None,
                risk_comment="execution=disabled; real_trading=disabled; watch alert only",
                reason=f"{asset_class}: close={close} > prev_high={prev_high}; atr_pct={atr_pct}; volume_ratio={volume_ratio}",
            )

            if dry_run:
                print(
                    "MULTI_ASSET_BREAKOUT_TELEGRAM_SENDER_DRY_RUN "
                    f"symbol={symbol} channel_type=RADAR target_env=TELEGRAM_MARKET_RADAR_CHAT_ID"
                )
                skipped += 1
                continue

            result = TelegramSignalDispatcher().dispatch(msg)
            print(
                "MULTI_ASSET_BREAKOUT_TELEGRAM_SENDER_RESULT "
                f"symbol={symbol} status={result.status} channel_type={result.channel_type} "
                f"target_env={result.target_env} reason={result.reason}"
            )
            sent += int(result.status == "sent")

    print()
    print("MULTI_ASSET_BREAKOUT_TELEGRAM_SENDER_SUMMARY")
    print(f"plan_ok={plan_ok}")
    print(f"telegram_decision={decision}")
    print(f"ready_rows={len(rows)}")
    print(f"telegram_dry_run={int(dry_run)}")
    print(f"telegram_sent={sent}")
    print(f"telegram_skipped={skipped}")
    print("db_update=0")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print(f"real_trading_enabled={os.getenv('REAL_TRADING_ENABLED', '0')}")
    print(f"execution_enabled={os.getenv('EXECUTION_ENABLED', '0')}")

    if not plan_ok:
        print("VERDICT=MULTI_ASSET_BREAKOUT_TELEGRAM_SENDER_PLAN_FAILED")
    elif decision == "SILENT":
        print("VERDICT=MULTI_ASSET_BREAKOUT_TELEGRAM_SENDER_SILENT_OK")
    elif dry_run:
        print("VERDICT=MULTI_ASSET_BREAKOUT_TELEGRAM_SENDER_DRY_RUN_READY")
    elif sent > 0:
        print("VERDICT=MULTI_ASSET_BREAKOUT_TELEGRAM_SENDER_SENT")
    else:
        print("VERDICT=MULTI_ASSET_BREAKOUT_TELEGRAM_SENDER_REVIEW_REQUIRED")

    print("MULTI_ASSET_BREAKOUT_TELEGRAM_SENDER_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
