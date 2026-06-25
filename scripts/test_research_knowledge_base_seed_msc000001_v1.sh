#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_RESEARCH_KNOWLEDGE_BASE_SEED_MSC000001_V1 ==="

python3 -m py_compile \
  src/scripts/research/seed_research_knowledge_base_msc000001_v1.py

src/scripts/research/seed_research_knowledge_base_msc000001_v1.py \
  | tee /tmp/research_knowledge_base_seed_msc000001_v1.out

grep -q "RESEARCH_KNOWLEDGE_BASE_SEED_MSC000001_V1" /tmp/research_knowledge_base_seed_msc000001_v1.out
grep -q "candidate_id=MSC-000001" /tmp/research_knowledge_base_seed_msc000001_v1.out
grep -q "status=REJECTED" /tmp/research_knowledge_base_seed_msc000001_v1.out
grep -q "status_reason=ROBUSTNESS_WEAK" /tmp/research_knowledge_base_seed_msc000001_v1.out
grep -q "db_update=1" /tmp/research_knowledge_base_seed_msc000001_v1.out
grep -q "VERDICT=RESEARCH_KNOWLEDGE_BASE_SEED_MSC000001_OK" /tmp/research_knowledge_base_seed_msc000001_v1.out

echo "TEST_RESEARCH_KNOWLEDGE_BASE_SEED_MSC000001_V1_OK"
