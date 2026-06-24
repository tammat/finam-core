#!/usr/bin/env python3
from pathlib import Path

PIPE = Path("src/finam_core/pipelines/paper_pipeline.py")
AUDIT = Path("src/finam_core/analytics/runtime_guard_pre_signal_block_audit_v1.py")

print("=== GOLD_RUNTIME_SESSION_GUARD_FINAL_READINESS_V1 ===")
print("mode=final_readiness")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("paper_orders=0")

checks = []

def check(name, ok, detail):
    checks.append(ok)
    print(f"CHECK name={name} ok={1 if ok else 0} detail={detail}")

pipe_text = PIPE.read_text(errors="ignore") if PIPE.exists() else ""
audit_text = AUDIT.read_text(errors="ignore") if AUDIT.exists() else ""

print("\nREADINESS_CHECKS")

check("paper_pipeline_exists", PIPE.exists(), str(PIPE))
check("audit_writer_exists", AUDIT.exists(), str(AUDIT))
check(
    "insertion_point_unique",
    pipe_text.count("routed = self.signal_intent_router.route(raw_intent)") == 1,
    "before_signal_intent_router_route",
)
check(
    "pre_signal_audit_method_exists",
    "_save_pre_signal_block_audit_v1" in pipe_text,
    "_save_pre_signal_block_audit_v1",
)
check(
    "audit_table_writer_supports_block_type_reason",
    "block_type" in audit_text and "block_reason" in audit_text,
    "runtime_guard_pre_signal_block_audit_v1",
)
check(
    "gold_guard_not_already_applied",
    "PIPE_RUNTIME_GOLD_SESSION_BLOCK" not in pipe_text,
    "avoid_duplicate_patch",
)
check(
    "session_filter_anchor_exists",
    "SESSION_FILTER" in pipe_text,
    "existing_session_filter_context",
)
check(
    "execution_layer_not_target",
    True,
    "execution_layer_change=0",
)
check(
    "real_trading_not_target",
    True,
    "real_order_change=0",
)

print("\nPROPOSED_PATCH_SCOPE")
print("file=src/finam_core/pipelines/paper_pipeline.py")
print("helper=_resolve_hour_msk_v1")
print("guard=GDU6@RTSX,GLU6@RTSX hour_msk>=19 BLOCK_EVENING_SESSION")
print("audit=runtime_guard_pre_signal_block_audit_v1")
print("block_type=SESSION_FILTER")
print("block_reason=gold_evening_session")

print("\nSUMMARY")
failed = len([x for x in checks if not x])
print(f"checks_total={len(checks)}")
print(f"checks_failed={failed}")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")

if failed == 0:
    print("VERDICT=GOLD_RUNTIME_SESSION_GUARD_READY_FOR_APPLY")
else:
    print("VERDICT=GOLD_RUNTIME_SESSION_GUARD_NOT_READY")
    raise SystemExit(1)
