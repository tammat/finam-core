#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_USD_GOVERNANCE_REPLAY_V1_START"

python -m py_compile src/scripts/analytics/build_usd_governance_replay_v1.py

python src/scripts/analytics/build_usd_governance_replay_v1.py \
  > /tmp/usd_governance_replay_v1.out

grep -q "USD_GOVERNANCE_REPLAY_V1" /tmp/usd_governance_replay_v1.out
grep -q "USD_GOVERNANCE_REPLAY_CONFIG" /tmp/usd_governance_replay_v1.out
grep -q "USD_GOVERNANCE_REPLAY_TOTAL" /tmp/usd_governance_replay_v1.out
grep -q "USD_GOVERNANCE_REPLAY_SYMBOL" /tmp/usd_governance_replay_v1.out
grep -q "USD_GOVERNANCE_PROFILE_TOP" /tmp/usd_governance_replay_v1.out
grep -q "USD_GOVERNANCE_REPLAY_V1_OK" /tmp/usd_governance_replay_v1.out

echo "TEST_USD_GOVERNANCE_REPLAY_V1_OK"
