#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
export PYTHONPATH=src

python3 -m py_compile \
  src/scripts/analytics/build_contract_selector_v2_liquidity_advisory.py

timeout 45s python3 src/scripts/analytics/build_contract_selector_v2_liquidity_advisory.py \
  | tee /tmp/contract_selector_v2_liquidity_advisory.log

grep -q "CONTRACT SELECTOR V2 LIQUIDITY ADVISORY" /tmp/contract_selector_v2_liquidity_advisory.log
grep -q "LIQUIDITY_ADVISORY_ROWS" /tmp/contract_selector_v2_liquidity_advisory.log
grep -q "LIQUIDITY_ROW root=BR" /tmp/contract_selector_v2_liquidity_advisory.log
grep -q "LIQUIDITY_ROW root=NG" /tmp/contract_selector_v2_liquidity_advisory.log
grep -q "CONTRACT_SELECTOR_V2_LIQUIDITY_ADVISORY_OK" /tmp/contract_selector_v2_liquidity_advisory.log

echo "TEST_CONTRACT_SELECTOR_V2_LIQUIDITY_ADVISORY_OK"
