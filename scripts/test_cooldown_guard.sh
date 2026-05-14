#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/strategy/cooldown_guard.py

python - <<'PY'
from finam_core.strategy.cooldown_guard import CooldownGuard

g = CooldownGuard()

assert g.calculate_dynamic_cooldown(base_cooldown=10, atr_pct=0.02) == 5
assert g.calculate_dynamic_cooldown(base_cooldown=10, atr_pct=0.001) == 15
assert g.calculate_dynamic_cooldown(base_cooldown=10, atr_pct=0.01) == 10

d = g.check_elapsed(last_ts=100, now_ts=105, cooldown_sec=10)
assert d.allowed is False
assert d.reason == "cooldown_active"

d = g.check_elapsed(last_ts=100, now_ts=111, cooldown_sec=10)
assert d.allowed is True

d1 = g.check(key="BRM6@RTSX:BUY", cooldown_sec=60)
assert d1.allowed is True

d2 = g.check(key="BRM6@RTSX:BUY", cooldown_sec=60)
assert d2.allowed is False

print("OK: CooldownGuard")
PY
