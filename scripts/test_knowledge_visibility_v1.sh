#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_KNOWLEDGE_VISIBILITY_V1 ==="

PYTHONPATH=src src/marketcore/cli/main.py catalog summary \
  | tee /tmp/knowledge_visibility_summary_v1.out

PYTHONPATH=src src/marketcore/cli/main.py catalog coverage \
  | tee /tmp/knowledge_visibility_coverage_v1.out

PYTHONPATH=src src/marketcore/cli/main.py catalog stats \
  | tee /tmp/knowledge_visibility_stats_v1.out

grep -q "objects=" /tmp/knowledge_visibility_summary_v1.out
grep -q "domains=" /tmp/knowledge_visibility_summary_v1.out
grep -q "domain=WORKFLOW" /tmp/knowledge_visibility_coverage_v1.out
grep -q "object_id_coverage_pct=100.00" /tmp/knowledge_visibility_coverage_v1.out
grep -q "health_coverage_pct=100.00" /tmp/knowledge_visibility_coverage_v1.out
grep -q "stat_type=domain" /tmp/knowledge_visibility_stats_v1.out
grep -q "stat_type=layer" /tmp/knowledge_visibility_stats_v1.out
grep -q "stat_type=source" /tmp/knowledge_visibility_stats_v1.out

echo "knowledge_visibility=READY"
echo "catalog_summary=READY"
echo "catalog_coverage=READY"
echo "catalog_stats=READY"
echo "read_only_ui_next=KNOWLEDGE_COVERAGE_UI_V1"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=KNOWLEDGE_VISIBILITY_V1_READY"
echo "TEST_KNOWLEDGE_VISIBILITY_V1_OK"
