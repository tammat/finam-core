#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/finam_core/analytics/symbol_strategy_mapper.py \
  src/finam_core/analytics/symbol_strategy_resolver.py

echo "TEST_SYMBOL_STRATEGY_RESOLVER_COMPILE_OK"
