#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile src/scripts/research/build_cross_market_regime_research_v1.py

python3 src/scripts/research/build_cross_market_regime_research_v1.py | \
  tee /tmp/cross_market_regime_research_v1.log

grep -q "CROSS MARKET REGIME RESEARCH V1" /tmp/cross_market_regime_research_v1.log
grep -q "mode=research_only" /tmp/cross_market_regime_research_v1.log
grep -q "TOP_COMPRESSION" /tmp/cross_market_regime_research_v1.log
grep -q "TOP_EXPANSION" /tmp/cross_market_regime_research_v1.log
grep -Eq "VERDICT=OK|VERDICT=NO_FEATURE_DATA" /tmp/cross_market_regime_research_v1.log

echo CROSS_MARKET_REGIME_RESEARCH_V1_OK
