#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST BR CLEAN CHAIN TEMPORAL DECAY V1 ==="

python -m py_compile \
  src/scripts/research/build_br_clean_chain_temporal_decay_v1.py

OUTPUT="$(
    PYTHONPATH=src \
    python src/scripts/research/build_br_clean_chain_temporal_decay_v1.py
)"

echo "$OUTPUT"

grep -q 'source=closed_trade_chains_v3' <<< "$OUTPUT"
grep -q 'quality_status=FULL' <<< "$OUTPUT"

grep -q \
  'CONTRACT_ROW symbol=BRM6@RTSX' \
  <<< "$OUTPUT"

grep -q \
  'CONTRACT_ROW symbol=BRN6@RTSX' \
  <<< "$OUTPUT"

grep -q \
  'CONTRACT_ROW symbol=BRQ6@RTSX trades=0' \
  <<< "$OUTPUT"

grep -q \
  'TEMPORAL_BUCKET_ROW bucket=EARLY' \
  <<< "$OUTPUT"

grep -q \
  'TEMPORAL_BUCKET_ROW bucket=MIDDLE' \
  <<< "$OUTPUT"

grep -q \
  'TEMPORAL_BUCKET_ROW bucket=RECENT' \
  <<< "$OUTPUT"

grep -q 'db_writes_performed=0' <<< "$OUTPUT"
grep -q 'runtime_allow=0' <<< "$OUTPUT"
grep -q 'execution_enabled=0' <<< "$OUTPUT"

grep -q \
  'VERDICT=BR_CLEAN_CHAIN_TEMPORAL_DECAY_V1_' \
  <<< "$OUTPUT"

echo
echo "=== DIFF CHECK ==="
git diff --check

echo
echo "VERDICT=TEST_BR_CLEAN_CHAIN_TEMPORAL_DECAY_V1_OK"
