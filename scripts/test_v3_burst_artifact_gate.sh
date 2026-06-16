#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"
export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/research/build_v3_burst_artifact_gate.py

python3 src/scripts/research/build_fill_pairing_engine_v3.py \
  | tee /tmp/fill_pairing_engine_v3_before_burst_gate.log

python3 src/scripts/research/build_trade_attribution_v3_from_chains_v3.py \
  | tee /tmp/trade_attribution_v3_before_burst_gate.log

python3 src/scripts/research/build_strategy_statistics_v3_from_attribution_v3.py \
  | tee /tmp/strategy_statistics_v3_before_burst_gate.log

python3 src/scripts/research/build_v3_burst_artifact_gate.py \
  | tee /tmp/v3_burst_artifact_gate.log

grep -q "V3 BURST ARTIFACT GATE" \
  /tmp/v3_burst_artifact_gate.log

grep -q "V3_BURST_ARTIFACT_GATE_SUMMARY" \
  /tmp/v3_burst_artifact_gate.log

grep -q "V3_BURST_ARTIFACT_GATE_OK" \
  /tmp/v3_burst_artifact_gate.log

unsafe_rows=$(psql "$DATABASE_URL" -At -c "
select count(*)
from v3_burst_artifact_gate
where burst_status='BURST_ARTIFACT'
  and (
       allow_statistics=true
    or allow_walkforward=true
    or allow_promotion=true
    or allow_runtime=true
    or runtime_allowed=true
    or execution_enabled=true
  );
")

echo "unsafe_burst_artifact_rows=${unsafe_rows}"

if [ "${unsafe_rows}" != "0" ]; then
  echo "FAIL: burst artifact is allowed downstream"
  exit 1
fi

brm6_burst_rows=$(psql "$DATABASE_URL" -At -c "
select count(*)
from v3_burst_artifact_gate
where symbol='BRM6@RTSX'
  and strategy='BR_CONSERVATIVE_BREAKOUT'
  and timeframe='M5'
  and quality_bucket='FULL_ONLY'
  and burst_status='BURST_ARTIFACT';
")

echo "brm6_full_burst_rows=${brm6_burst_rows}"

if [ "${brm6_burst_rows}" != "1" ]; then
  echo "FAIL: expected BRM6 FULL_ONLY to be marked as BURST_ARTIFACT"
  exit 1
fi

echo TEST_V3_BURST_ARTIFACT_GATE_OK
