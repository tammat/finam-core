#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

PIPE = Path("src/finam_core/pipelines/paper_pipeline.py")

print("=== GOLD_RUNTIME_SESSION_GUARD_PATCH_DRY_RUN_V1 ===")
print("mode=patch_dry_run")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")

if not PIPE.exists():
    print("VERDICT=PAPER_PIPELINE_NOT_FOUND")
    raise SystemExit(1)

lines = PIPE.read_text(errors="ignore").splitlines()

candidates = []

KEYWORDS = [
    "signal_emit",
    "intent_create",
    "signal_router",
    "signal_intent_router",
    "pre_signal",
    "_save_pre_signal",
]

for idx, line in enumerate(lines, start=1):
    low = line.lower()
    if any(k.lower() in low for k in KEYWORDS):
        candidates.append((idx, line.strip()))

print("\nPATCH_INSERTION_CANDIDATES")

for idx, text in candidates[:50]:
    safe = text.replace(" ", "_")
    print(
        f"PATCH_CANDIDATE line={idx} text={safe[:240]}"
    )

print("\nSIMULATED_GUARD")

print("IF symbol in {GDU6@RTSX,GLU6@RTSX}")
print("AND hour_msk >= 19")
print("THEN BLOCK_EVENING_SESSION")

print("\nSIMULATED_LOG")

print(
    "PIPE_RUNTIME_GOLD_SESSION_BLOCK "
    "symbol=GDU6@RTSX "
    "decision=BLOCK_EVENING_SESSION "
    "reason=gold_evening_session"
)

print("\nSIMULATED_AUDIT")

print("table=runtime_guard_pre_signal_block_audit_v1")
print("block_type=SESSION_FILTER")
print("block_reason=gold_evening_session")

print("\nPATCH_GUARDRAILS")

print("paper_pipeline_modified=0")
print("runtime_modified=0")
print("execution_modified=0")
print("real_trading_enabled=0")

print("\nSUMMARY")

print(f"candidate_lines={len(candidates)}")

if candidates:
    print("VERDICT=GOLD_RUNTIME_SESSION_GUARD_PATCH_DRY_RUN_READY")
else:
    print("VERDICT=NO_INSERTION_POINT_FOUND")
    raise SystemExit(1)
