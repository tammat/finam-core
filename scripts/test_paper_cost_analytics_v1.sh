#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core
export PYTHONPATH=src

echo "TEST_PAPER_COST_ANALYTICS_V1_START"

python -m py_compile src/scripts/analytics/build_paper_cost_analytics_v1.py

python src/scripts/analytics/build_paper_cost_analytics_v1.py \
  > /tmp/paper_cost_analytics_v1.out

grep -q "PAPER_COST_ANALYTICS_V1" /tmp/paper_cost_analytics_v1.out
grep -q "PAPER_COST_CONFIG" /tmp/paper_cost_analytics_v1.out
grep -q "PAPER_COST_SUMMARY" /tmp/paper_cost_analytics_v1.out
grep -q "PAPER_COST_ANALYTICS_V1_OK" /tmp/paper_cost_analytics_v1.out

echo "TEST_PAPER_COST_ANALYTICS_V1_OK"
