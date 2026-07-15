#!/usr/bin/env bash
set -euo pipefail
cd /opt/finam-core
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src venv/bin/pytest -q tests/test_profit_funnel_contract_v2.py
echo "funnel_stages=10"
echo "real_test_scope_isolation=PASS"
echo "cohort_reconciliation=PASS"
echo "freshness_quality_boundary=PASS"
echo "source_lineage_required=PASS"
echo "VERDICT=MARKETCORE_STAGE7_PROFIT_FUNNEL_CONTRACT_V2_READY"
