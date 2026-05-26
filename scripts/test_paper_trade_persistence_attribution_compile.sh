#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile src/finam_core/pipelines/paper_pipeline.py

grep -q '"symbol": br_signal.symbol' src/finam_core/pipelines/paper_pipeline.py
grep -q '"strategy": br_strategy' src/finam_core/pipelines/paper_pipeline.py
grep -q '"timeframe": "M5"' src/finam_core/pipelines/paper_pipeline.py
grep -q 'strategy=trade_payload.get("strategy")' src/finam_core/pipelines/paper_pipeline.py
grep -q 'timeframe=trade_payload.get("timeframe")' src/finam_core/pipelines/paper_pipeline.py

echo "PAPER_TRADE_PERSISTENCE_ATTRIBUTION_COMPILE_OK"
