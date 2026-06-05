#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile src/scripts/research/build_cross_market_regime_signal_quality_v1.py

python3 src/scripts/research/build_cross_market_regime_signal_quality_v1.py | \
  tee /tmp/cross_market_regime_signal_quality_v1.log

grep -q "CROSS MARKET REGIME SIGNAL QUALITY V1" /tmp/cross_market_regime_signal_quality_v1.log
grep -q "mode=research_only" /tmp/cross_market_regime_signal_quality_v1.log
grep -q "timeframe=M5" /tmp/cross_market_regime_signal_quality_v1.log
grep -Eq "VERDICT=OK|VERDICT=NO_CLOSED_TRADES" /tmp/cross_market_regime_signal_quality_v1.log

echo CROSS_MARKET_REGIME_SIGNAL_QUALITY_V1_OK
