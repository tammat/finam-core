#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_RESEARCH_KNOWLEDGE_BASE_VALIDATION_V1 ==="

python3 -m py_compile \
  src/scripts/research/build_research_knowledge_base_validation_v1.py

src/scripts/research/build_research_knowledge_base_validation_v1.py \
  | tee /tmp/research_knowledge_base_validation_v1.out

grep -q "RESEARCH_KNOWLEDGE_BASE_VALIDATION_V1" /tmp/research_knowledge_base_validation_v1.out
grep -q "candidates=" /tmp/research_knowledge_base_validation_v1.out
grep -q "decisions=" /tmp/research_knowledge_base_validation_v1.out
grep -q "hypotheses=" /tmp/research_knowledge_base_validation_v1.out
grep -q "knowledge_events=" /tmp/research_knowledge_base_validation_v1.out
grep -q "msc000001_exists=1" /tmp/research_knowledge_base_validation_v1.out
grep -q "msc000001_hypothesis=1" /tmp/research_knowledge_base_validation_v1.out
grep -q "duplicate_candidates=0" /tmp/research_knowledge_base_validation_v1.out
grep -q "VERDICT=RESEARCH_KNOWLEDGE_BASE_VALIDATION_OK" /tmp/research_knowledge_base_validation_v1.out

echo "TEST_RESEARCH_KNOWLEDGE_BASE_VALIDATION_V1_OK"
