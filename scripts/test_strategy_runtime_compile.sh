#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/strategy/strategy_runtime.py \
  src/finam_core/pipelines/paper_pipeline.py

grep -q "class StrategyRuntime" src/finam_core/strategy/strategy_runtime.py
grep -q "self.strategy_runtime = StrategyRuntime()" src/finam_core/pipelines/paper_pipeline.py
grep -q "self.strategy_runtime.on_quote(sym, st)" src/finam_core/pipelines/paper_pipeline.py

echo "OK: strategy runtime compile"
