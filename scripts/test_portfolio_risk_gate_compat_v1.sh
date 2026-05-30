#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_PORTFOLIO_RISK_GATE_COMPAT_V1_START"

python -m py_compile \
  src/finam_core/pipelines/paper_pipeline.py \
  src/finam_core/risk/portfolio_risk_gate.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text()

assert 'hasattr(gate, "evaluate")' in text
assert 'hasattr(gate, "check")' in text
assert 'gate.check(symbol=str(sym))' in text
assert "PIPE_PORTFOLIO_RISK_GATE_SKIP_NO_METHOD" in text
assert "PIPE_PORTFOLIO_RISK_OK" in text

print("TEST_PORTFOLIO_RISK_GATE_COMPAT_V1_OK")
PY
