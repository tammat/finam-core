#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_MARKET_INDEX_SOURCE_DECISION_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_market_index_source_decision_v1.py

src/scripts/research/build_market_index_source_decision_v1.py \
  | tee /tmp/market_index_source_decision_v1.out

grep -q "MARKET_INDEX_SOURCE_DECISION_V1" /tmp/market_index_source_decision_v1.out
grep -q "primary_feature_source=public.feature_snapshots" /tmp/market_index_source_decision_v1.out
grep -q "index=USD_RUB status=AVAILABLE" /tmp/market_index_source_decision_v1.out
grep -q "index=BR status=AVAILABLE" /tmp/market_index_source_decision_v1.out
grep -q "decision=USE_AVAILABLE_CONTEXT_FIRST" /tmp/market_index_source_decision_v1.out
grep -q "context_v1=FX_USDRUB" /tmp/market_index_source_decision_v1.out
grep -q "context_v1=ENERGY_BR" /tmp/market_index_source_decision_v1.out
grep -q "rule=do_not_mix_index_context_into_instrument_signature_v1" /tmp/market_index_source_decision_v1.out
grep -q "VERDICT=MARKET_INDEX_SOURCE_DECISION_READY" /tmp/market_index_source_decision_v1.out

echo "TEST_MARKET_INDEX_SOURCE_DECISION_V1_OK"
