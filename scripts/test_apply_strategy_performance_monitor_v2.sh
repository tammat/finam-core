#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/apply_strategy_performance_monitor_v2.py

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/apply_strategy_performance_monitor_v2.py").read_text(encoding="utf-8")

assert "analytics_strategy_performance_monitor_v2" in text
assert "strategy_runtime_control" in text
assert "on conflict (symbol, strategy) do update" in text
assert "risk_multiplier" in text
assert "spm_v2:" in text

print("OK: SPM v2 applier static check")
PY
