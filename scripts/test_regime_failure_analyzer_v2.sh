#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/analyze_regime_failures_v2.py

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/analyze_regime_failures_v2.py").read_text(encoding="utf-8")

assert "analytics_strategy_regime_attribution_v2" in text
assert "FAILURE_ZONE" in text
assert "NO_DATA" in text
assert "avg_signed_cashflow" in text

print("OK: RegimeFailureAnalyzer v2 static check")
PY

PYTHONPATH=src python src/scripts/analyze_regime_failures_v2.py
