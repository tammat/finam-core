#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_RESEARCH_KNOWLEDGE_BASE_SCHEMA_DRY_RUN_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_research_knowledge_base_schema_dry_run_v1.py

src/scripts/research/build_research_knowledge_base_schema_dry_run_v1.py \
  | tee /tmp/research_knowledge_base_schema_dry_run_v1.out

grep -q "RESEARCH_KNOWLEDGE_BASE_SCHEMA_DRY_RUN_V1" /tmp/research_knowledge_base_schema_dry_run_v1.out
grep -q "CREATE TABLE IF NOT EXISTS research.research_candidates_v1" /tmp/research_knowledge_base_schema_dry_run_v1.out
grep -q "CREATE TABLE IF NOT EXISTS research.research_candidate_decisions_v1" /tmp/research_knowledge_base_schema_dry_run_v1.out
grep -q "CREATE TABLE IF NOT EXISTS research.research_hypotheses_v1" /tmp/research_knowledge_base_schema_dry_run_v1.out
grep -q "CREATE TABLE IF NOT EXISTS research.research_knowledge_events_v1" /tmp/research_knowledge_base_schema_dry_run_v1.out
grep -q "guard=no_db_execute" /tmp/research_knowledge_base_schema_dry_run_v1.out
grep -q "rule=candidate_id_is_immutable" /tmp/research_knowledge_base_schema_dry_run_v1.out
grep -q "VERDICT=RESEARCH_KNOWLEDGE_BASE_SCHEMA_DRY_RUN_READY" /tmp/research_knowledge_base_schema_dry_run_v1.out

echo "TEST_RESEARCH_KNOWLEDGE_BASE_SCHEMA_DRY_RUN_V1_OK"
