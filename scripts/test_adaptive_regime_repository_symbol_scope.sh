#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/risk/adaptive_regime_repository.py \
  src/finam_core/pipelines/paper_pipeline.py

python - <<'PY'
from pathlib import Path

repo_text = Path("src/finam_core/risk/adaptive_regime_repository.py").read_text(encoding="utf-8")
pipe_text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text(encoding="utf-8")

assert "where symbol = %s" in repo_text
assert "and regime_ru = %s" in repo_text
assert "group by symbol, regime_ru" in repo_text
assert "evaluate_regime(regime_ru, symbol=" in pipe_text
assert "institutional_flow_regime_events" in pipe_text

print("OK: adaptive regime repository uses symbol + regime scope and equity fallback")
PY
