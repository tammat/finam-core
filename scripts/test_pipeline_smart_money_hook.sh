#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/pipelines/paper_pipeline.py \
  src/finam_core/orderflow/smart_money_features.py \
  src/finam_core/orderflow/smart_money_feature_repository.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text(encoding="utf-8")

checks = [
    "ENABLE_SMART_MONEY_FEATURES",
    "SMART_MONEY_MIN_SCORE",
    "SMART_MONEY_SAVE_INTERVAL_SEC",
    "SmartMoneyFeatureLayer",
    "SmartMoneyFeatureRepository",
    "PIPE_SMART_MONEY_FEATURE",
]

for c in checks:
    assert c in text, c

impl = text.split("def _on_quote_impl", 1)[1]
assert "self._record_smart_money_features_if_enabled(" in impl

session_pos = impl.find("PIPE_SESSION_BLOCK")
hook_pos = impl.find("self._record_smart_money_features_if_enabled(")

assert hook_pos != -1
assert session_pos != -1
assert hook_pos < session_pos

print("OK: paper_pipeline smart money live hook before session gate")
PY
