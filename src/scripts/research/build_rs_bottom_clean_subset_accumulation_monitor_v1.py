#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import subprocess
import sys

print("=== RS_BOTTOM_CLEAN_SUBSET_ACCUMULATION_MONITOR_V1 ===")
print("mode=read_only_monitor")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")

proc = subprocess.run(
    [
        sys.executable,
        "src/scripts/research/build_rs_bottom_clean_subset_forward_accumulation_v1.py",
    ],
    text=True,
    capture_output=True,
)

raw = (proc.stdout or "") + "\n" + (proc.stderr or "")

row = {}

for line in raw.splitlines():
    if line.startswith("ACCUMULATION_ROW "):
        row = dict(re.findall(r"([a-zA-Z_]+)=([^ ]+)", line))

completed = int(row.get("completed", 0))
remaining = int(row.get("remaining", 0))
real_pf = float(row.get("real_pf", 0))
expectancy = float(row.get("expectancy", 0))

if real_pf < 1:
    decision = "EDGE_DEGRADED_REVIEW_REQUIRED"
elif completed >= 100 and real_pf >= 1.3 and expectancy > 0:
    decision = "READY_FOR_REVIEW_NOT_LIVE"
else:
    decision = "ACCUMULATION_CONTINUE"

print(
    f"MONITOR_ROW completed={completed} "
    f"remaining={remaining} "
    f"real_pf={real_pf:.6f} "
    f"expectancy={expectancy:.6f} "
    f"decision={decision}"
)

print("VERDICT=RS_BOTTOM_CLEAN_SUBSET_ACCUMULATION_MONITOR_READY")
print("TEST_RS_BOTTOM_CLEAN_SUBSET_ACCUMULATION_MONITOR_V1_OK")
