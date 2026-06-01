#!/usr/bin/env python3

import os
import re
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path("/opt/finam-core")
SCRIPT = PROJECT_ROOT / "src/scripts/analytics/build_accumulation_plan_v1.py"

python_bin = sys.executable

env = os.environ.copy()
env["PYTHONPATH"] = str(PROJECT_ROOT / "src")

result = subprocess.run(
    [python_bin, str(SCRIPT)],
    cwd=str(PROJECT_ROOT),
    env=env,
    capture_output=True,
    text=True,
)

if result.returncode != 0:
    print("=== KPI ИССЛЕДОВАТЕЛЬСКОГО КОНТУРА ===")
    print("ОШИБКА: build_accumulation_plan_v1.py завершился с ошибкой")
    print(result.stderr.strip())
    sys.exit(0)

rows = []

for line in result.stdout.splitlines():
    if "ACCUMULATION_PLAN_ROW" not in line:
        continue

    symbol = re.search(r"symbol=([^ ]+)", line)
    trades = re.search(r"current_trades=([0-9]+)", line)
    action = re.search(r"action=([^ ]+)", line)

    if symbol and trades and action:
        rows.append({
            "symbol": symbol.group(1),
            "trades": int(trades.group(1)),
            "action": action.group(1),
        })

ready = [r for r in rows if r["action"] == "READY_FOR_NEXT_VALIDATION"]
progress = [r for r in rows if r["action"] == "CONTINUE_PAPER_ACCUMULATION"]

print("=== KPI ИССЛЕДОВАТЕЛЬСКОГО КОНТУРА ===")
print()
print("ИНСТРУМЕНТ     СДЕЛКИ   ГОТОВНОСТЬ")
print()

for row in sorted(ready, key=lambda x: x["trades"], reverse=True):
    symbol = row["symbol"].replace("@MISX", "").replace("@RTSX", "")
    print(f"{symbol:<12} {row['trades']:>6}    ГОТОВ")

print()

for row in sorted(progress, key=lambda x: x["trades"], reverse=True):
    symbol = row["symbol"].replace("@MISX", "").replace("@RTSX", "")
    pct = min(100, row["trades"])
    print(f"{symbol:<12} {row['trades']:>6}    {pct}%")

print()
print("ИТОГО:")
print(f"ГОТОВЫ={len(ready)}")
print(f"В РАБОТЕ={len(progress)}")
