#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/runtime/regime_runtime_override_repository.py \
  src/finam_core/risk/runtime_override_gate.py

python - <<'PY'
from finam_core.risk.runtime_override_gate import apply_runtime_override_gate
from finam_core.runtime.regime_runtime_override_repository import RuntimeRegimeOverrideState

block = RuntimeRegimeOverrideState(
    strategy="S",
    root_symbol="BR",
    regime="M5",
    runtime_action="BLOCK",
    max_position_size=0.0,
    allowed_execution_mode="blocked",
    risk_multiplier=0.0,
    cooldown_sec=3600,
    stop_take_profile="no_entry",
    reason="regime_matrix_block",
)
d = apply_runtime_override_gate(
    requested_quantity=10,
    execution_mode="paper",
    override=block,
)
assert d.allowed is False
assert d.adjusted_quantity == 0.0
assert d.risk_multiplier == 0.0

watch = RuntimeRegimeOverrideState(
    strategy="S",
    root_symbol="BR",
    regime="LIVE",
    runtime_action="WATCH",
    max_position_size=0.5,
    allowed_execution_mode="paper",
    risk_multiplier=0.5,
    cooldown_sec=900,
    stop_take_profile="conservative",
    reason="regime_matrix_watch",
)
d = apply_runtime_override_gate(
    requested_quantity=10,
    execution_mode="paper",
    override=watch,
)
assert d.allowed is True
assert d.adjusted_quantity == 5.0
assert d.risk_multiplier == 0.5
assert d.stop_take_profile == "conservative"

d = apply_runtime_override_gate(
    requested_quantity=10,
    execution_mode="real",
    override=watch,
)
assert d.allowed is False
assert "mode_block" in d.reason

d = apply_runtime_override_gate(
    requested_quantity=10,
    execution_mode="paper",
    override=None,
)
assert d.allowed is True
assert d.adjusted_quantity == 10.0

print("RUNTIME_OVERRIDE_GATE_UNIT_OK")
PY

grep -q "runtime_regime_overrides" src/finam_core/runtime/regime_runtime_override_repository.py
grep -q "apply_runtime_override_gate" src/finam_core/risk/runtime_override_gate.py

echo "RUNTIME_OVERRIDE_GATE_TEST_OK"
