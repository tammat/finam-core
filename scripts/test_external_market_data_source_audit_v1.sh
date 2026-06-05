#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile src/scripts/research/build_external_market_data_source_audit_v1.py

python3 src/scripts/research/build_external_market_data_source_audit_v1.py | \
  tee /tmp/external_market_data_source_audit_v1.log

grep -q "EXTERNAL MARKET DATA SOURCE AUDIT V1" /tmp/external_market_data_source_audit_v1.log
grep -q "BTCUSD" /tmp/external_market_data_source_audit_v1.log
grep -q "ETHUSD" /tmp/external_market_data_source_audit_v1.log
grep -q "SPY" /tmp/external_market_data_source_audit_v1.log
grep -q "EURUSD" /tmp/external_market_data_source_audit_v1.log
grep -q "SOURCE_RECOMMENDED_CRYPTO" /tmp/external_market_data_source_audit_v1.log
grep -q "SOURCE_RECOMMENDED_ETF" /tmp/external_market_data_source_audit_v1.log
grep -q "SOURCE_RECOMMENDED_FX" /tmp/external_market_data_source_audit_v1.log
grep -q "VERDICT=READY_FOR_PROVIDER_ABSTRACTION" /tmp/external_market_data_source_audit_v1.log

echo EXTERNAL_MARKET_DATA_SOURCE_AUDIT_V1_OK
