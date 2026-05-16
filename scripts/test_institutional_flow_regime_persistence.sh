#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

psql "$DATABASE_URL" -v ON_ERROR_STOP=1 \
  -f scripts/create_institutional_flow_regime_events.sql >/dev/null

python -m py_compile \
  src/finam_core/orderflow/institutional_flow_regime.py \
  src/scripts/classify_institutional_flow_regime.py

python - <<'PY'
from pathlib import Path

text = Path("src/scripts/classify_institutional_flow_regime.py").read_text(encoding="utf-8")

checks = [
    "InstitutionalFlowRegimeEngine",
    "smart_money_feature_events",
    "institutional_flow_regime_events",
    "engine.classify",
    "classify_institutional_flow_regime",
]

for c in checks:
    assert c in text, c

print("OK: institutional flow regime persistence static check")
PY

PYTHONPATH=src python src/scripts/classify_institutional_flow_regime.py
