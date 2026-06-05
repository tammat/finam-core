#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile \
  src/finam_core/research/market_data_provider.py \
  src/scripts/research/test_binance_public_klines_research_provider_v1.py

python3 src/scripts/research/test_binance_public_klines_research_provider_v1.py | \
  tee /tmp/binance_public_klines_research_provider_v1.log

grep -q "BINANCE_PUBLIC_KLINES_RESEARCH_PROVIDER_V1_OK" \
  /tmp/binance_public_klines_research_provider_v1.log

echo TEST_BINANCE_PUBLIC_KLINES_RESEARCH_PROVIDER_V1_OK
