#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/finam_core/research/futures_mtf_regime_aggregator.py \
  src/scripts/build_futures_mtf_regime.py

grep -q "futures_mtf_regime" src/finam_core/research/futures_mtf_regime_aggregator.py
grep -q "bias_alignment" src/finam_core/research/futures_mtf_regime_aggregator.py
grep -q "FUTURES_MTF_REGIME_SUMMARY" src/scripts/build_futures_mtf_regime.py

echo "TEST_FUTURES_MTF_REGIME_AGGREGATOR_OK"
