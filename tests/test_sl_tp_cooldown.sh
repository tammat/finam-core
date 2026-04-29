#!/usr/bin/env bash
set -euo pipefail

PYTHONPATH=src python - <<'PY'
from finam_core.risk.sl_tp_cooldown import SlTpCooldownEngine

e = SlTpCooldownEngine()

assert e.evaluate("BR", 1, 100, 99.6).should_exit is True
assert e.evaluate("BR", 1, 100, 99.6).reason == "stop_loss_long"
assert e.evaluate("BR", 1, 100, 100.7).reason == "take_profit_long"

assert e.evaluate("BR", -1, 100, 100.4).reason == "stop_loss_short"
assert e.evaluate("BR", -1, 100, 99.3).reason == "take_profit_short"

assert e.evaluate("BR", 0, 100, 101).should_exit is False

e.mark_exit("BR")
assert e.is_cooldown("BR") is True

print("OK sl_tp_cooldown")
PY
