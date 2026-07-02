#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_KNOWLEDGE_GRAPH_VALIDATION_V1 ==="

scripts/apply_knowledge_graph_validation_v1.sh

PYTHONPATH=src python -m py_compile \
  src/scripts/build_knowledge_graph_validation_v1.py

KG_DOMAIN=PAPER_RUNTIME DATABASE_URL=postgresql:///finam_core PYTHONPATH=src \
python src/scripts/build_knowledge_graph_validation_v1.py \
  | tee /tmp/knowledge_graph_validation_v1.txt

grep -q "VERDICT=KNOWLEDGE_GRAPH_VALIDATION_V1_READY" \
  /tmp/knowledge_graph_validation_v1.txt

psql -d finam_core -c "
SELECT run_id, domain, status, total_findings, started_at, finished_at
FROM knowledge_graph.validation_runs
ORDER BY run_id DESC
LIMIT 3;
"

psql -d finam_core -c "
SELECT check_code, severity, count(*)
FROM knowledge_graph.validation_findings
GROUP BY check_code, severity
ORDER BY severity, check_code;
"

echo "VERDICT=TEST_KNOWLEDGE_GRAPH_VALIDATION_V1_OK"
