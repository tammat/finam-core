#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/research/research_regime_classifier.py

python - <<'PY'
from finam_core.research.research_regime_classifier import (
    RegimeInput,
    ResearchRegimeClassifier,
)

clf = ResearchRegimeClassifier()

up = clf.classify(RegimeInput(
    symbol="SBER@MISX",
    open=100,
    high=104,
    low=99,
    close=103,
    prev_close=100,
    avg_range_pct=0.02,
))
assert up.trend == "trend_up"

down = clf.classify(RegimeInput(
    symbol="SBER@MISX",
    open=100,
    high=101,
    low=96,
    close=97,
    prev_close=100,
    avg_range_pct=0.02,
))
assert down.trend == "trend_down"

squeeze = clf.classify(RegimeInput(
    symbol="SBER@MISX",
    open=100,
    high=100.4,
    low=99.8,
    close=100.1,
    prev_close=100,
    avg_range_pct=0.02,
))
assert squeeze.trend == "squeeze"

print("OK: research regime classifier")
PY
