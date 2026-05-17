#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/runtime/runtime_universe_allocator.py \
  src/finam_core/analytics/strategy_rank_weight_provider.py

echo "OK: RuntimeUniverseAllocator v2 compile"
