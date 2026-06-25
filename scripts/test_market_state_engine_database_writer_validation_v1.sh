#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_MARKET_STATE_ENGINE_DATABASE_WRITER_VALIDATION_V1 ==="

python3 -m py_compile \
src/scripts/research/build_market_state_engine_database_writer_validation_v1.py

src/scripts/research/build_market_state_engine_database_writer_validation_v1.py \
| tee /tmp/market_state_engine_database_writer_validation_v1.out

grep -q "MARKET_STATE_ENGINE_DATABASE_WRITER_VALIDATION_V1" \
/tmp/market_state_engine_database_writer_validation_v1.out

grep -q "VERDICT=OK" \
/tmp/market_state_engine_database_writer_validation_v1.out

echo "TEST_MARKET_STATE_ENGINE_DATABASE_WRITER_VALIDATION_V1_OK"
