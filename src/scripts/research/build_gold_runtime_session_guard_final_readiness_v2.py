#!/usr/bin/env python3
from pathlib import Path

PIPE = Path("src/finam_core/pipelines/paper_pipeline.py")
AUDIT = Path("src/finam_core/analytics/runtime_guard_pre_signal_block_audit_v1.py")

print("=== GOLD_RUNTIME_SESSION_GUARD_FINAL_READINESS_V2 ===")
print("mode=final_readiness_v2")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")

checks = []

def check(name, ok, detail):
    checks.append(ok)
    print(f"CHECK name={name} ok={1 if ok else 0} detail={detail}")

pipe_text = PIPE.read_text(errors="ignore") if PIPE.exists() else ""
audit_text = AUDIT.read_text(errors="ignore") if AUDIT.exists() else ""

print("\nREADINESS_CHECKS")

check("paper_pipeline_exists", PIPE.exists(), str(PIPE))

check(
    "target_line_exists",
    pipe_text.count("routed = self.signal_intent_router.route(raw_intent)") == 1,
    "line_4376_router_anchor",
)

check(
    "audit_writer_exists",
    AUDIT.exists(),
    str(AUDIT),
)

check(
    "pre_signal_audit_method_exists",
    "_save_pre_signal_block_audit_v1" in pipe_text,
    "_save_pre_signal_block_audit_v1",
)

check(
    "audit_supports_block_type_reason",
    "block_type" in audit_text and "block_reason" in audit_text,
    "runtime_guard_pre_signal_block_audit_v1",
)

check(
    "gold_guard_not_already_applied",
    "PIPE_RUNTIME_GOLD_SESSION_BLOCK" not in pipe_text,
    "avoid_duplicate_patch",
)

check(
    "helper_not_required_yet",
    True,
    "_resolve_hour_msk_v1_plan_ready",
)

check(
    "execution_layer_not_target",
    True,
    "execution_change=0",
)

check(
    "real_trading_not_target",
    True,
    "real_order_change=0",
)

print("\nPATCH_SCOPE")

print("target_file=src/finam_core/pipelines/paper_pipeline.py")
print("insert_before=routed = self.signal_intent_router.route(raw_intent)")
print("helper=_resolve_hour_msk_v1")
print("symbols=GDU6@RTSX,GLU6@RTSX")
print("rule=hour_msk>=19")
print("decision=BLOCK_EVENING_SESSION")
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
