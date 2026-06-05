#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile src/scripts/research/build_research_universe_expansion_audit_v1.py

python3 src/scripts/research/build_research_universe_expansion_audit_v1.py | \
  tee /tmp/research_universe_expansion_audit_v1.log

grep -q "RESEARCH UNIVERSE EXPANSION AUDIT V1" /tmp/research_universe_expansion_audit_v1.log
grep -q "CURRENT_UNIVERSE" /tmp/research_universe_expansion_audit_v1.log
grep -q "TARGET_UNIVERSE" /tmp/research_universe_expansion_audit_v1.log
grep -q "BTCUSD" /tmp/research_universe_expansion_audit_v1.log
grep -q "ETHUSD" /tmp/research_universe_expansion_audit_v1.log
grep -q "SPY" /tmp/research_universe_expansion_audit_v1.log
grep -q "QQQ" /tmp/research_universe_expansion_audit_v1.log
grep -q "EURUSD" /tmp/research_universe_expansion_audit_v1.log
grep -q "VERDICT=READY_FOR_DATA_COLLECTION_AUDIT_ONLY" /tmp/research_universe_expansion_audit_v1.log

echo RESEARCH_UNIVERSE_EXPANSION_AUDIT_V1_OK
