#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

PIPE = Path("src/finam_core/pipelines/paper_pipeline.py")
TARGET = "routed = self.signal_intent_router.route(raw_intent)"

print("=== GOLD_RUNTIME_SESSION_GUARD_IMPLEMENTATION_DRY_RUN_V1 ===")
print("mode=implementation_dry_run")
print("db_update=0")
print("paper_pipeline_modified=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("paper_orders=0")

text = PIPE.read_text(errors="ignore")
lines = text.splitlines()

matches = [
    (idx, line)
    for idx, line in enumerate(lines, start=1)
    if TARGET.replace(" ", "") in line.replace(" ", "")
]

print("\nTARGET_MATCHES")
for idx, line in matches:
    print(f"TARGET_MATCH line={idx} text={line.strip().replace(' ', '_')}")

if len(matches) != 1:
    print(f"VERDICT=GOLD_RUNTIME_SESSION_GUARD_IMPLEMENTATION_DRY_RUN_BAD_MATCH_COUNT count={len(matches)}")
    raise SystemExit(1)

line_no, target_line = matches[0]
indent = target_line[: len(target_line) - len(target_line.lstrip())]

snippet = f'''{indent}# Русский комментарий: блокируем вечерние gold-сигналы после сохранения signal telemetry, но до intent routing.
{indent}try:
{indent}    _gold_guard_symbol = getattr(raw_intent, "symbol", None) or sym
{indent}    _gold_guard_ts = getattr(raw_intent, "ts", None) or getattr(raw_intent, "timestamp", None)
{indent}    _gold_guard_hour_msk = _resolve_hour_msk_v1(_gold_guard_ts)
{indent}    if _gold_guard_symbol in {{"GDU6@RTSX", "GLU6@RTSX"}} and _gold_guard_hour_msk >= 19:
{indent}        print(
{indent}            f"PIPE_RUNTIME_GOLD_SESSION_BLOCK symbol={{_gold_guard_symbol}} "
{indent}            f"hour_msk={{_gold_guard_hour_msk}} decision=BLOCK_EVENING_SESSION "
{indent}            f"reason=gold_evening_session",
{indent}            flush=True,
{indent}        )
{indent}        self._save_pre_signal_block_audit_v1(
{indent}            symbol=_gold_guard_symbol,
{indent}            strategy=getattr(raw_intent, "strategy", None),
{indent}            timeframe=getattr(raw_intent, "timeframe", None),
{indent}            ts=_gold_guard_ts,
{indent}            block_type="SESSION_FILTER",
{indent}            block_reason="gold_evening_session",
{indent}            payload={{
{indent}                "decision": "BLOCK_EVENING_SESSION",
{indent}                "hour_msk": _gold_guard_hour_msk,
{indent}                "source": "gold_runtime_session_guard_v1",
{indent}            }},
{indent}        )
{indent}        return
{indent}except Exception as exc:
{indent}    print(f"PIPE_RUNTIME_GOLD_SESSION_GUARD_ERROR error={{exc}}", flush=True)
'''

print("\nDRY_RUN_INSERTION")
print(f"insert_before_line={line_no}")
print("insert_before_target=routed = self.signal_intent_router.route(raw_intent)")
print("decision=BLOCK_EVENING_SESSION")
print("block_type=SESSION_FILTER")
print("block_reason=gold_evening_session")

print("\nSIMULATED_PATCH_SNIPPET_BEGIN")
print(snippet.rstrip())
print("SIMULATED_PATCH_SNIPPET_END")

print("\nGUARDRAILS")
print("paper_pipeline_modified=0")
print("execution_layer_change=0")
print("real_order_change=0")
print("db_schema_change=0")
print("runtime_enable_change=0")

print("\nVERDICT=GOLD_RUNTIME_SESSION_GUARD_IMPLEMENTATION_DRY_RUN_READY")
