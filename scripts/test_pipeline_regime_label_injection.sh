#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/regime/regime_labeler.py \
  src/finam_core/pipelines/paper_pipeline.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text(encoding="utf-8")

assert "from finam_core.regime.regime_labeler import RegimeLabeler" in text
assert "RegimeLabeler.label(" in text
assert 'raw_intent["features"]["regime_label"] = regime_label' in text
assert 'raw_intent["regime"] = regime_label' in text
assert 'raw_intent.features["regime_label"] = regime_label' in text
assert "raw_intent.regime = regime_label" in text

print("OK: pipeline injects regime_label into SignalIntent payload")
PY
