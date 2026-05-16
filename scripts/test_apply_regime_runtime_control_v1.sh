#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/scripts/apply_regime_runtime_control_v1.py

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/apply_regime_runtime_control_v1.py").read_text(encoding="utf-8")

assert "analytics_strategy_regime_attribution_v2" in text
assert "strategy_runtime_regime_control" in text
assert "on conflict (symbol, strategy, regime) do update" in text
assert "regime_applier_v1:" in text
assert "risk_multiplier" in text

print("OK: regime runtime-control applier static check")
PY
