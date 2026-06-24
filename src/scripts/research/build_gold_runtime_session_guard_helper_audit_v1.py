#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path("src")

PATTERNS = [
    "hour_msk",
    "Europe/Moscow",
    "timezone",
    "ZoneInfo",
    "astimezone",
    "_resolve_hour_msk",
    "signal_ts at time zone",
]

print("=== GOLD_RUNTIME_SESSION_GUARD_HELPER_AUDIT_V1 ===")
print("mode=read_only")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")

hits = []

for py_file in ROOT.rglob("*.py"):
    try:
        lines = py_file.read_text(errors="ignore").splitlines()
    except Exception:
        continue

    for idx, line in enumerate(lines, start=1):
        low = line.lower()
        if any(p.lower() in low for p in PATTERNS):
            hits.append((str(py_file), idx, line.strip()))

print("\nHELPER_CANDIDATES")

for file_name, line_no, text in hits[:200]:
    safe = text.replace(" ", "_")
    print(
        f"HELPER_HIT "
        f"file={file_name} "
        f"line={line_no} "
        f"text={safe[:240]}"
    )

print("\nEXPECTED_HELPER")

print("helper_name=_resolve_hour_msk_v1")
print("input=datetime")
print("output=hour_msk")
print("timezone=Europe/Moscow")

print("\nSUMMARY")
print(f"hits_total={len(hits)}")

if hits:
    print("VERDICT=GOLD_RUNTIME_SESSION_GUARD_HELPER_AUDIT_READY")
else:
    print("VERDICT=NO_TIMEZONE_HELPER_FOUND")
    raise SystemExit(1)
