#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/research/runtime_selection_gate.py

python - <<'PY'
from finam_core.research.runtime_selection_gate import normalize_root_symbol

assert normalize_root_symbol("NGF6@RTSX") == "NG"
assert normalize_root_symbol("NGM6@RTSX") == "NG"
assert normalize_root_symbol("BRM6@RTSX") == "BR"
assert normalize_root_symbol("SBER@MISX") == "SBER@MISX"

print("RUNTIME_SELECTION_GATE_NORMALIZATION_OK")
PY

python - <<'PY'
from finam_core.research.runtime_selection_gate import RuntimeSelectionGate

gate = RuntimeSelectionGate()

ok = gate.is_allowed(
    strategy="NG_CONSERVATIVE_BREAKOUT",
    symbol="NGM6@RTSX",
    regime="LOW_VOL",
)

assert ok.allowed is True
assert ok.root_symbol == "NG"

bad = gate.is_allowed(
    strategy="NG_CONSERVATIVE_BREAKOUT",
    symbol="NGM6@RTSX",
    regime="TREND_DOWN",
)

assert bad.allowed is False

print("RUNTIME_SELECTION_GATE_DB_OK")
PY
