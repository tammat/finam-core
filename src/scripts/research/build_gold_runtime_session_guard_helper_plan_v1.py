#!/usr/bin/env python3

print("=== GOLD_RUNTIME_SESSION_GUARD_HELPER_PLAN_V1 ===")
print("mode=plan_only")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("paper_orders=0")

print("\nHELPER_TARGET")

print("file=src/finam_core/pipelines/paper_pipeline.py")
print("helper_name=_resolve_hour_msk_v1")
print("timezone=Europe/Moscow")

print("\nHELPER_IMPORTS")

print("from datetime import datetime")
print("from zoneinfo import ZoneInfo")

print("\nHELPER_BODY")

print("MSK = ZoneInfo('Europe/Moscow')")

print("def _resolve_hour_msk_v1(ts) -> int:")
print("    if ts is None:")
print("        return -1")
print("    if getattr(ts, 'tzinfo', None) is None:")
print("        return -1")
print("    return ts.astimezone(MSK).hour")

print("\nHELPER_USAGE")

print("hour_msk = _resolve_hour_msk_v1(signal_ts)")
print("if hour_msk >= 19:")
print("    BLOCK_EVENING_SESSION")

print("\nDEPENDENCY_CHECK")

print("new_modules=0")
print("new_tables=0")
print("new_services=0")
print("new_configs=0")

print("\nGUARDRAILS")

print("execution_change=0")
print("real_order_change=0")
print("runtime_enable_change=0")
print("db_schema_change=0")

print("\nVERDICT=GOLD_RUNTIME_SESSION_GUARD_HELPER_PLAN_READY")
