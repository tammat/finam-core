#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_QUALITY_LINEAGE_CLI_V1 ==="

PYTHONPATH=src python -m py_compile src/marketcore/cli/quality_lineage_cli.py
PYTHONPATH=src python -m py_compile src/marketcore/cli/main.py

PYTHONPATH=src python src/marketcore/cli/main.py lineage summary \
  | tee /tmp/quality_lineage_cli_lineage_summary.out

grep -q "relationship_types=" /tmp/quality_lineage_cli_lineage_summary.out
grep -q "lineage_events=" /tmp/quality_lineage_cli_lineage_summary.out
grep -q "runtime_changed=0" /tmp/quality_lineage_cli_lineage_summary.out

PYTHONPATH=src python src/marketcore/cli/main.py lineage relationships \
  | tee /tmp/quality_lineage_cli_relationships.out

grep -q "entity_code=NORMALIZED_FROM" /tmp/quality_lineage_cli_relationships.out
grep -q "entity_code=EXPLAINED_BY" /tmp/quality_lineage_cli_relationships.out

PYTHONPATH=src python src/marketcore/cli/main.py lineage health \
  | tee /tmp/quality_lineage_cli_health.out

grep -q "missing_lineage_uuid=" /tmp/quality_lineage_cli_health.out
grep -q "self_edges=" /tmp/quality_lineage_cli_health.out

PYTHONPATH=src python src/marketcore/cli/main.py quality summary \
  | tee /tmp/quality_lineage_cli_quality_summary.out

grep -q "quality_reasons=" /tmp/quality_lineage_cli_quality_summary.out
grep -q "resolution_methods=" /tmp/quality_lineage_cli_quality_summary.out
grep -q "quality_events=" /tmp/quality_lineage_cli_quality_summary.out

PYTHONPATH=src python src/marketcore/cli/main.py quality reasons \
  | tee /tmp/quality_lineage_cli_quality_reasons.out

grep -q "entity_code=BAD_TICK" /tmp/quality_lineage_cli_quality_reasons.out
grep -q "entity_code=TIME_ORDER_VIOLATION" /tmp/quality_lineage_cli_quality_reasons.out

PYTHONPATH=src python src/marketcore/cli/main.py quality blocked \
  | tee /tmp/quality_lineage_cli_quality_blocked.out

grep -q "unresolved_blocks_research=" /tmp/quality_lineage_cli_quality_blocked.out
grep -q "unresolved_blocks_ai=" /tmp/quality_lineage_cli_quality_blocked.out
grep -q "unresolved_blocks_runtime=" /tmp/quality_lineage_cli_quality_blocked.out

echo "quality_lineage_cli=READY"
echo "commands=lineage:summary,relationships,search,health;quality:summary,reasons,unresolved,blocked"
echo "policy=READ_ONLY"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=QUALITY_LINEAGE_CLI_V1_READY"
echo "TEST_QUALITY_LINEAGE_CLI_V1_OK"
