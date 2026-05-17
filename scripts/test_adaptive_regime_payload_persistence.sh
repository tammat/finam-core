#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/pipelines/paper_pipeline.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text(encoding="utf-8")

checks = [
    'payload.setdefault("adaptive_regime_action", features.get("adaptive_regime_action"))',
    'payload.setdefault("adaptive_regime_multiplier", features.get("adaptive_regime_multiplier"))',
    'payload.setdefault("adaptive_regime_reason", features.get("adaptive_regime_reason"))',
    'payload.setdefault("institutional_flow_regime_ru", features.get("institutional_flow_regime_ru"))',
]

for c in checks:
    assert c in text, c

print("OK: adaptive regime fields persisted into trade payload")
PY
