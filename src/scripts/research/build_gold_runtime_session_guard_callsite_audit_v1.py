#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

TARGET_FILES = [
    "src/finam_core/pipelines/paper_pipeline.py",
    "src/finam_core/analytics/runtime_guard_decision_adapter_v1.py",
    "src/finam_core/analytics/runtime_guard_pre_signal_block_audit_v1.py",
    "src/finam_core/governance/runtime_guard_reader.py",
    "src/finam_core/runtime/runtime_governance_engine.py",
]

PATTERNS = [
    "pre_signal",
    "runtime_guard",
    "runtime_guard_pre_signal_block_audit_v1",
    "block_reason",
    "block_type",
    "BLOCK",
    "guard",
    "signal",
]

EXCLUDED_PREFIXES = [
    "src/finam_core/execution/",
    "src/finam_core/adapters/grpc/orders_client.py",
    "src/finam_core/risk/futures_real_block_guard_v1.py",
]

print("=== GOLD_RUNTIME_SESSION_GUARD_CALLSITE_AUDIT_V1 ===")
print("mode=read_only")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")

print("\nTARGET_FILES")
for f in TARGET_FILES:
    print(f"TARGET_FILE {f}")

print("\nCALLSITE_ROWS")

hits_total = 0
missing_files = 0

for file_name in TARGET_FILES:
    p = Path(file_name)
    if not p.exists():
        missing_files += 1
        print(f"CALLSITE_ROW file={file_name} status=MISSING hits=0")
        continue

    lines = p.read_text(errors="ignore").splitlines()
    file_hits = []

    for idx, line in enumerate(lines, start=1):
        low = line.lower()
        if any(pattern.lower() in low for pattern in PATTERNS):
            file_hits.append((idx, line.strip()))

    hits_total += len(file_hits)

    print(
        "CALLSITE_ROW "
        f"file={file_name} "
        f"status=FOUND "
        f"hits={len(file_hits)}"
    )

    for line_no, text in file_hits[:30]:
        safe = text.replace(" ", "_")
        print(
            "CALLSITE_HIT "
            f"file={file_name} "
            f"line={line_no} "
            f"text={safe[:240]}"
        )

print("\nEXCLUDED_LAYERS")
for prefix in EXCLUDED_PREFIXES:
    print(f"EXCLUDED_LAYER {prefix}")

print("\nPROPOSED_INSERTION")
print("preferred_file=src/finam_core/pipelines/paper_pipeline.py")
print("preferred_stage=pre_signal_guard_before_signal_emit_or_before_intent_create")
print("audit_writer=src/finam_core/analytics/runtime_guard_pre_signal_block_audit_v1.py")
print("decision_reason=gold_evening_session")
print("decision=BLOCK_EVENING_SESSION")
print("rule=symbol in {GDU6@RTSX,GLU6@RTSX} and hour_msk >= 19")

print("\nGUARDRAILS")
print("do_not_touch_execution_layer=1")
print("do_not_touch_real_orders=1")
print("do_not_enable_runtime=1")
print("do_not_update_db=1")

print("\nSUMMARY")
print(f"target_files={len(TARGET_FILES)}")
print(f"missing_files={missing_files}")
print(f"hits_total={hits_total}")

if missing_files == 0 and hits_total > 0:
    print("VERDICT=GOLD_RUNTIME_SESSION_GUARD_CALLSITE_AUDIT_READY")
else:
    print("VERDICT=GOLD_RUNTIME_SESSION_GUARD_CALLSITE_AUDIT_INCOMPLETE")
    raise SystemExit(1)
