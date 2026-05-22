#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/finam_core/research/futures_regime_engine.py \
  src/scripts/build_futures_regime_engine.py

grep -q "FuturesRegimeEngine" src/finam_core/research/futures_regime_engine.py
grep -q "market_bars" src/finam_core/research/futures_regime_engine.py
grep -q "futures_regime_engine_v1" src/finam_core/research/futures_regime_engine.py
grep -q "FUTURES_REGIME_ENGINE_SUMMARY" src/scripts/build_futures_regime_engine.py

echo "TEST_FUTURES_REGIME_ENGINE_OK"
