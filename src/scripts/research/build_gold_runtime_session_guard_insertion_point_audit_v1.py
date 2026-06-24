#!/usr/bin/env python3
from pathlib import Path

PIPE = Path("src/finam_core/pipelines/paper_pipeline.py")

print("=== GOLD_RUNTIME_SESSION_GUARD_INSERTION_POINT_AUDIT_V1 ===")
print("mode=read_only")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")

lines = PIPE.read_text(errors="ignore").splitlines()

targets = [
    "raw_intent = self.signal_router.route(",
    "routed = self.signal_intent_router.route(raw_intent)",
]

print("\nINSERTION_POINTS")

for target in targets:
    found = False

    for idx, line in enumerate(lines, start=1):
        if target.replace(" ", "") in line.replace(" ", ""):
            found = True

            start = max(0, idx - 8)
            end = min(len(lines), idx + 8)

            print(
                f"INSERTION_POINT line={idx} "
                f"target={target}"
            )

            for n in range(start, end):
                text = lines[n].strip().replace(" ", "_")
                print(
                    f"CONTEXT line={n+1} text={text[:240]}"
                )

            print()

    if not found:
        print(f"INSERTION_POINT_NOT_FOUND target={target}")

print("\nEVALUATION")

print("OPTION_A=before_signal_router_route")
print("OPTION_B=before_signal_intent_router_route")

print("\nEXPECTED_BEHAVIOR")

print("A blocks signal generation completely")
print("B allows signal generation but blocks intent creation")

print("\nRECOMMENDATION")

print("preferred=OPTION_B")
print("reason=preserve signal telemetry and analytics")
print("audit_writer=runtime_guard_pre_signal_block_audit_v1")

print("\nVERDICT=GOLD_RUNTIME_SESSION_GUARD_INSERTION_POINT_READY")
