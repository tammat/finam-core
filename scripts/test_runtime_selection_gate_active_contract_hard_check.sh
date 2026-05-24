#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/research/runtime_selection_gate.py \
  src/finam_core/research/active_contract_lifecycle_filter.py

grep -q "runtime_hard_check_rejected" src/finam_core/research/runtime_selection_gate.py
grep -q "closed_trade_quality_stats" src/finam_core/research/runtime_selection_gate.py
grep -q "active_symbol_for_root_symbol" src/finam_core/research/runtime_selection_gate.py

python - <<'PY'
from finam_core.research.runtime_selection_gate import RuntimeSelectionGate

gate = RuntimeSelectionGate()

decision = gate.is_allowed(
    strategy="NG_CONSERVATIVE_BREAKOUT",
    symbol="NGM6@RTSX",
    regime="LOW_VOL",
)

print(
    "RUNTIME_GATE_HARD_CHECK_RESULT "
    f"allowed={decision.allowed} "
    f"reason={decision.reason}"
)

# Сейчас PROMOTED_RUNTIME должен быть пустой или активный NGM6 не подтвержден.
assert decision.allowed is False

print("RUNTIME_SELECTION_GATE_ACTIVE_CONTRACT_HARD_CHECK_OK")
PY
