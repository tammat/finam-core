#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_RESEARCH_KNOWLEDGE_BASE_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_research_knowledge_base_v1.py

src/scripts/research/build_research_knowledge_base_v1.py \
  | tee /tmp/research_knowledge_base_v1.out

grep -q "RESEARCH_KNOWLEDGE_BASE_V1" /tmp/research_knowledge_base_v1.out
grep -q "candidate_id=MSC-000001" /tmp/research_knowledge_base_v1.out
grep -q "status=REJECTED" /tmp/research_knowledge_base_v1.out
grep -q "status_reason=ROBUSTNESS_WEAK" /tmp/research_knowledge_base_v1.out
grep -q "table=research.research_candidates_v1" /tmp/research_knowledge_base_v1.out
grep -q "rule=candidate_id_is_immutable" /tmp/research_knowledge_base_v1.out
grep -q "VERDICT=RESEARCH_KNOWLEDGE_BASE_PLAN_READY" /tmp/research_knowledge_base_v1.out

echo "TEST_RESEARCH_KNOWLEDGE_BASE_V1_OK"
