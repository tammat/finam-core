#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import re

ROOT = Path("src")

TARGET_PATTERNS = [
    "runtime_pre_signal_guard",
    "pre_signal_guard",
    "runtime_guard_pre_signal_block_audit_v1",
    "PIPE_RUNTIME",
    "PIPE_EQUITY",
    "BLOCK_",
    "guard_decision",
]

print("=== GOLD_RUNTIME_SESSION_GUARD_INTEGRATION_PLAN_V1 ===")
print("mode=integration_audit")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")

hits = []

for py_file in ROOT.rglob("*.py"):
    try:
        text = py_file.read_text(errors="ignore")
    except Exception:
        continue

    for pattern in TARGET_PATTERNS:
        if pattern in text:
            hits.append((str(py_file), pattern))

print("\nINTEGRATION_CANDIDATES")

shown = set()

for file_name, pattern in sorted(hits):
    key = (file_name,)
    if key in shown:
        continue
    shown.add(key)

    print(
        f"INTEGRATION_CANDIDATE "
        f"file={file_name}"
    )

print("\nPROPOSED_GUARD")

print("RULE=symbol in {GDU6@RTSX,GLU6@RTSX}")
print("AND=hour_msk >= 19")
print("THEN=BLOCK_EVENING_SESSION")
print("ELSE=ALLOW_RESEARCH_SHADOW")

print("\nEXPECTED_WRITER")

print("audit_table=runtime_guard_pre_signal_block_audit_v1")
print("block_reason=gold_evening_session")
print("block_type=SESSION_FILTER")

print("\nGUARD_TARGET")

print("preferred_layer=runtime_pre_signal_guard")
print("fallback_layer=paper_pipeline_pre_signal_guard")
print("execution_layer=NO_CHANGE")
print("real_trading=NO_CHANGE")

print("\nVERDICT=GOLD_RUNTIME_SESSION_GUARD_INTEGRATION_PLAN_READY")
