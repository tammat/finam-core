#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile src/scripts/observability/build_research_feature_freshness_health_v1.py

python3 src/scripts/observability/build_research_feature_freshness_health_v1.py | \
  tee /tmp/research_feature_freshness_health_v1.log

grep -q "RESEARCH FEATURE FRESHNESS HEALTH V1" /tmp/research_feature_freshness_health_v1.log
grep -q "mode=research_only" /tmp/research_feature_freshness_health_v1.log
grep -q "FEATURE_HEALTH_ROW symbol=BTCUSD timeframe=M1" /tmp/research_feature_freshness_health_v1.log
grep -q "FEATURE_HEALTH_ROW symbol=ETHUSD timeframe=M5" /tmp/research_feature_freshness_health_v1.log
grep -q "SUMMARY" /tmp/research_feature_freshness_health_v1.log
grep -Eq "VERDICT=OK|VERDICT=FEATURE_HEALTH_MISSING|VERDICT=FEATURE_HEALTH_STALE|VERDICT=FEATURE_HEALTH_WEAK_HISTORY|VERDICT=NO_FEATURE_STORE_TABLE" /tmp/research_feature_freshness_health_v1.log

echo RESEARCH_FEATURE_FRESHNESS_HEALTH_V1_OK
