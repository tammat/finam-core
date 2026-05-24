#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH="${PYTHONPATH:-src}"

python -m py_compile \
  src/finam_core/research/ng_regime_classifier.py \
  src/scripts/research/build_ng_regime_analytics.py

grep -q "HIGH_VOL_TREND_UP" \
  src/finam_core/research/ng_regime_classifier.py

grep -q "COMPRESSION" \
  src/finam_core/research/ng_regime_classifier.py

grep -q "NG_REGIME_ANALYTICS_SUMMARY" \
  src/scripts/research/build_ng_regime_analytics.py

echo "TEST_NG_REGIME_ANALYTICS_OK"
