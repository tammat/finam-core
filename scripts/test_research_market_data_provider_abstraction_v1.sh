#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile \
  src/finam_core/research/market_data_provider.py \
  src/scripts/research/test_research_market_data_provider_abstraction_v1.py

python3 src/scripts/research/test_research_market_data_provider_abstraction_v1.py | \
  tee /tmp/research_market_data_provider_abstraction_v1.log

grep -q "RESEARCH_MARKET_DATA_PROVIDER_ABSTRACTION_V1_OK" \
  /tmp/research_market_data_provider_abstraction_v1.log

echo TEST_RESEARCH_MARKET_DATA_PROVIDER_ABSTRACTION_V1_OK
