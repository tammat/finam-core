#!/usr/bin/env python3
from pathlib import Path

PIPE = Path("src/finam_core/pipelines/paper_pipeline.py")
TARGET = "routed = self.signal_intent_router.route(raw_intent)"

print("=== GOLD_RUNTIME_SESSION_GUARD_SHADOW_APPLY_V1 ===")
print("mode=shadow_apply")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("default_blocking=0")

text = PIPE.read_text(errors="ignore")

if "PIPE_RUNTIME_GOLD_SESSION_BLOCK" in text:
    print("VERDICT=GOLD_RUNTIME_SESSION_GUARD_ALREADY_APPLIED")
    raise SystemExit(1)

if text.count(TARGET) != 1:
    print(f"VERDICT=BAD_TARGET_COUNT count={text.count(TARGET)}")
    raise SystemExit(1)

helper = '''
def _resolve_hour_msk_v1(ts) -> int:
    """Русский комментарий: локальный helper для gold session guard."""
    try:
        if ts is None:
            return -1
        if getattr(ts, "tzinfo", None) is None:
            return -1
        from zoneinfo import ZoneInfo
        return int(ts.astimezone(ZoneInfo("Europe/Moscow")).hour)
    except Exception:
        return -1
'''

if "_resolve_hour_msk_v1" not in text:
    marker = "class "
    idx = text.find(marker)
    if idx < 0:
        print("VERDICT=CLASS_ANCHOR_NOT_FOUND")
        raise SystemExit(1)
    text = text[:idx] + helper + "\n\n" + text[idx:]

guard = '''        # GOLD_RUNTIME_SESSION_GUARD_SHADOW_APPLY_V1:
        # Русский комментарий: в shadow-режиме фиксируем вечерний gold-block, но не ломаем общий поток.
        try:
            _gold_guard_symbol = None
            if isinstance(raw_intent, dict):
                _gold_guard_symbol = raw_intent.get("symbol") or sym
                _gold_guard_ts = raw_intent.get("ts") or raw_intent.get("timestamp")
                _gold_guard_strategy = raw_intent.get("strategy")
                _gold_guard_timeframe = raw_intent.get("timeframe")
            else:
                _gold_guard_symbol = getattr(raw_intent, "symbol", None) or sym
                _gold_guard_ts = getattr(raw_intent, "ts", None) or getattr(raw_intent, "timestamp", None)
                _gold_guard_strategy = getattr(raw_intent, "strategy", None)
                _gold_guard_timeframe = getattr(raw_intent, "timeframe", None)

            _gold_guard_hour_msk = _resolve_hour_msk_v1(_gold_guard_ts)

            if str(_gold_guard_symbol) in {"GDU6@RTSX", "GLU6@RTSX"} and _gold_guard_hour_msk >= 19:
                print(
                    f"PIPE_RUNTIME_GOLD_SESSION_BLOCK symbol={_gold_guard_symbol} "
                    f"hour_msk={_gold_guard_hour_msk} decision=BLOCK_EVENING_SESSION "
                    f"reason=gold_evening_session mode=shadow",
                    flush=True,
                )
                self._save_pre_signal_block_audit_v1(
                    symbol=str(_gold_guard_symbol),
                    strategy=_gold_guard_strategy,
                    timeframe=_gold_guard_timeframe,
                    ts=_gold_guard_ts,
                    block_type="SESSION_FILTER",
                    block_reason="gold_evening_session",
                    payload={
                        "decision": "BLOCK_EVENING_SESSION",
                        "mode": "shadow",
                        "hour_msk": _gold_guard_hour_msk,
                        "source": "gold_runtime_session_guard_shadow_apply_v1",
                    },
                )
                if os.getenv("GOLD_SESSION_GUARD_BLOCK_ENABLED", "0") == "1":
                    return
        except Exception as exc:
            print(f"PIPE_RUNTIME_GOLD_SESSION_GUARD_ERROR error={exc}", flush=True)

'''

text = text.replace(TARGET, guard + TARGET, 1)
PIPE.write_text(text)

print("patched_file=src/finam_core/pipelines/paper_pipeline.py")
print("insert_before=routed = self.signal_intent_router.route(raw_intent)")
print("shadow_default=1")
print("blocking_env=GOLD_SESSION_GUARD_BLOCK_ENABLED")
print("VERDICT=GOLD_RUNTIME_SESSION_GUARD_SHADOW_APPLY_READY")
