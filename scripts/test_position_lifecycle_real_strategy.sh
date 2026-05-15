#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/pipelines/paper_pipeline.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text(encoding="utf-8")

assert "lifecycle_strategy = self._strategy_name_for_symbol(symbol)" in text
assert "strategy=lifecycle_strategy" in text
assert 'strategy="default"' not in text[1900:2200]
assert "BR_CONSERVATIVE_BREAKOUT_M5" not in text
assert "BR_CONSERVATIVE_BREAKOUT" in text

print("OK: PositionLifecycle uses real strategy key and BR key is normalized")
PY
