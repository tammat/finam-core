#!/usr/bin/env python3
from __future__ import annotations

print("=== GOLD_RUNTIME_SESSION_GUARD_PATCH_PLAN_V1 ===")
print("mode=patch_plan_only")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("paper_orders=0")

print("\nTARGET")

print("file=src/finam_core/pipelines/paper_pipeline.py")
print("layer=pre_signal_guard")
print("before=signal_emit")
print("before=intent_create")

print("\nGUARD_RULE")

print("symbols=GDU6@RTSX,GLU6@RTSX")
print("condition=hour_msk>=19")
print("decision=BLOCK_EVENING_SESSION")

print("\nAUDIT_WRITER")

print("file=src/finam_core/analytics/runtime_guard_pre_signal_block_audit_v1.py")
print("block_type=SESSION_FILTER")
print("block_reason=gold_evening_session")

print("\nEXPECTED_LOG")

print("PIPE_RUNTIME_GOLD_SESSION_BLOCK")
print("symbol=GDU6@RTSX|GLU6@RTSX")
print("decision=BLOCK_EVENING_SESSION")
print("reason=gold_evening_session")

print("\nEXPECTED_AUDIT_ROW")

print("table=runtime_guard_pre_signal_block_audit_v1")
print("block_type=SESSION_FILTER")
print("block_reason=gold_evening_session")

print("\nGUARDRAILS")

print("execution_layer_change=0")
print("real_order_change=0")
print("db_schema_change=0")
print("runtime_enable_change=0")

print("\nPATCH_PLAN_SUMMARY")

print("insert_guard=1")
print("insert_audit=1")
print("insert_log=1")
print("execution_change=0")
print("real_change=0")

print("VERDICT=GOLD_RUNTIME_SESSION_GUARD_PATCH_PLAN_READY")
