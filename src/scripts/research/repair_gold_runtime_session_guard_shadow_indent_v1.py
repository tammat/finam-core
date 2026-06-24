#!/usr/bin/env python3
from pathlib import Path

PIPE = Path("src/finam_core/pipelines/paper_pipeline.py")
MARKER = "# GOLD_RUNTIME_SESSION_GUARD_SHADOW_APPLY_V1:"
TARGET_STRIPPED = "routed = self.signal_intent_router.route(raw_intent)"
IND = "        "

text = PIPE.read_text(errors="ignore")
lines = text.splitlines()

marker_lines = [i for i, line in enumerate(lines) if MARKER in line]
if len(marker_lines) != 1:
    print(f"BAD_MARKER_COUNT count={len(marker_lines)}")
    raise SystemExit(1)

start = marker_lines[0]

end = None
for i in range(start, min(len(lines), start + 120)):
    if lines[i].strip() == TARGET_STRIPPED:
        end = i
        break

if end is None:
    print("TARGET_AFTER_MARKER_NOT_FOUND")
    raise SystemExit(1)

guard = f'''{IND}# GOLD_RUNTIME_SESSION_GUARD_SHADOW_APPLY_V1:
{IND}# Русский комментарий: shadow-режим фиксирует вечерний gold-block, но не ломает общий поток.
{IND}try:
{IND}    _gold_guard_symbol = None
{IND}    if isinstance(raw_intent, dict):
{IND}        _gold_guard_symbol = raw_intent.get("symbol") or sym
{IND}        _gold_guard_ts = raw_intent.get("ts") or raw_intent.get("timestamp")
{IND}        _gold_guard_strategy = raw_intent.get("strategy")
{IND}        _gold_guard_timeframe = raw_intent.get("timeframe")
{IND}    else:
{IND}        _gold_guard_symbol = getattr(raw_intent, "symbol", None) or sym
{IND}        _gold_guard_ts = getattr(raw_intent, "ts", None) or getattr(raw_intent, "timestamp", None)
{IND}        _gold_guard_strategy = getattr(raw_intent, "strategy", None)
{IND}        _gold_guard_timeframe = getattr(raw_intent, "timeframe", None)

{IND}    _gold_guard_hour_msk = _resolve_hour_msk_v1(_gold_guard_ts)

{IND}    if str(_gold_guard_symbol) in {{"GDU6@RTSX", "GLU6@RTSX"}} and _gold_guard_hour_msk >= 19:
{IND}        print(
{IND}            f"PIPE_RUNTIME_GOLD_SESSION_BLOCK symbol={{_gold_guard_symbol}} "
{IND}            f"hour_msk={{_gold_guard_hour_msk}} decision=BLOCK_EVENING_SESSION "
{IND}            f"reason=gold_evening_session mode=shadow",
{IND}            flush=True,
{IND}        )
{IND}        self._save_pre_signal_block_audit_v1(
{IND}            symbol=str(_gold_guard_symbol),
{IND}            strategy=_gold_guard_strategy,
{IND}            timeframe=_gold_guard_timeframe,
{IND}            ts=_gold_guard_ts,
{IND}            block_type="SESSION_FILTER",
{IND}            block_reason="gold_evening_session",
{IND}            payload={{
{IND}                "decision": "BLOCK_EVENING_SESSION",
{IND}                "mode": "shadow",
{IND}                "hour_msk": _gold_guard_hour_msk,
{IND}                "source": "gold_runtime_session_guard_shadow_apply_v1",
{IND}            }},
{IND}        )
{IND}        if os.getenv("GOLD_SESSION_GUARD_BLOCK_ENABLED", "0") == "1":
{IND}            return
{IND}except Exception as exc:
{IND}    print(f"PIPE_RUNTIME_GOLD_SESSION_GUARD_ERROR error={{exc}}", flush=True)

{IND}{TARGET_STRIPPED}'''.splitlines()

new_lines = lines[:start] + guard + lines[end + 1:]
PIPE.write_text("\n".join(new_lines) + "\n")

print("REPAIRED_GOLD_RUNTIME_SESSION_GUARD_SHADOW_INDENT_V1")
print(f"replaced_lines={start + 1}-{end + 1}")
print("VERDICT=GOLD_RUNTIME_SESSION_GUARD_SHADOW_INDENT_REPAIRED")
