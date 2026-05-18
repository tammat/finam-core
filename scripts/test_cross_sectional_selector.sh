#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/research/cross_sectional_selector.py

python - <<'PY'
from finam_core.research.cross_sectional_selector import (
    CrossSectionalSelector,
    InstrumentPerformance,
)

selector = CrossSectionalSelector()

items = [
    InstrumentPerformance("LKOH@MISX", 10, 100.0, 10.0, 0.5),
    InstrumentPerformance("PLZL@MISX", 8, 80.0, 8.0, 0.6),
    InstrumentPerformance("SBER@MISX", 10, -5.0, -0.5, 0.4),
    InstrumentPerformance("GAZP@MISX", 1, 20.0, 20.0, 1.0),
]

selected = selector.select(items, top_n=2, min_trades=3)

assert len(selected) == 2
assert selected[0].symbol == "LKOH@MISX"
assert selected[1].symbol == "PLZL@MISX"
assert selected[0].decision == "ВЫБРАТЬ"

print("OK: cross sectional selector")
PY
