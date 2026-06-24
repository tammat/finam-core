#!/usr/bin/env python3
from pathlib import Path

PIPE = Path("src/finam_core/pipelines/paper_pipeline.py")
TARGET = "routed = self.signal_intent_router.route(raw_intent)"

print("=== GOLD_RUNTIME_SESSION_GUARD_SESSION_ANCHOR_AUDIT_V1 ===")
print("mode=read_only")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")

text = PIPE.read_text(errors="ignore")
lines = text.splitlines()

matches = [
    (idx, line)
    for idx, line in enumerate(lines, start=1)
    if TARGET.replace(" ", "") in line.replace(" ", "")
]

print("\nTARGET")
print(f"target={TARGET}")
print(f"matches={len(matches)}")

if len(matches) != 1:
    print("VERDICT=SESSION_ANCHOR_TARGET_NOT_UNIQUE")
    raise SystemExit(1)

target_line, _ = matches[0]
start = max(1, target_line - 40)
end = min(len(lines), target_line + 80)

anchors = []

ANCHOR_PATTERNS = [
    "SESSION_FILTER",
    "ROUTER",
    "routed = self.signal_intent_router.route(raw_intent)",
    "_should_log_routed_signal",
    "return",
    "PIPE_",
    "_save_pre_signal_block_audit_v1",
    "runtime_guard",
    "block",
]

print("\nCONTEXT_ROWS")
for n in range(start, end + 1):
    raw = lines[n - 1]
    compact = raw.strip().replace(" ", "_")
    print(f"CONTEXT_ROW line={n} text={compact[:260]}")

    low = raw.lower()
    for p in ANCHOR_PATTERNS:
        if p.lower() in low:
            anchors.append((n, p, raw.strip()))

print("\nANCHOR_ROWS")
for n, pattern, raw in anchors:
    print(
        "ANCHOR_ROW "
        f"line={n} "
        f"pattern={pattern} "
        f"text={raw.replace(' ', '_')[:260]}"
    )

print("\nRECOMMENDATION")
print(f"target_line={target_line}")
print("preferred_anchor=ROUTER_BLOCK")
print("preferred_insert_before=routed = self.signal_intent_router.route(raw_intent)")
print("reason=signal_telemetry_preserved_and_intent_creation_blocked")
print("session_filter_anchor_required=0")
print("use_target_line_as_anchor=1")

print("\nSUMMARY")
print(f"anchors_found={len(anchors)}")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("VERDICT=GOLD_RUNTIME_SESSION_GUARD_SESSION_ANCHOR_AUDIT_READY")
