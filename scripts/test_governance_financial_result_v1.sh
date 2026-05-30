#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

echo "TEST_GOVERNANCE_FINANCIAL_RESULT_V1_START"

bash -n scripts/check_governance_financial_result_v1.sh

grep -q "GOVERNANCE_FINANCIAL_RESULT_V1" scripts/check_governance_financial_result_v1.sh
grep -q "runtime_governance_live_accumulation_v1" scripts/check_governance_financial_result_v1.sh
grep -q "ng_m1_runtime_policy" scripts/check_governance_financial_result_v1.sh
grep -q "closed_trades" scripts/check_governance_financial_result_v1.sh
grep -q "diagnostic_status" scripts/check_governance_financial_result_v1.sh

echo "TEST_GOVERNANCE_FINANCIAL_RESULT_V1_OK"
