#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/pipelines/paper_pipeline.py \
  src/finam_core/adapters/grpc/market_data.py

python - <<'PY'
from pathlib import Path

text = Path("src/finam_core/pipelines/paper_pipeline.py").read_text(encoding="utf-8")

checks = [
    'marketdata.ensure_subscribed(decision.active_symbols)',
    'PIPE_RUNTIME_MD_RESUBSCRIBE',
    'PIPE_RUNTIME_MD_RESUBSCRIBE_ERROR',
]

for c in checks:
    assert c in text, c

print("OK: paper_pipeline runtime MarketData resubscribe")
PY
