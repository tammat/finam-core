#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_RESEARCH_KNOWLEDGE_BASE_SCHEMA_APPLY_V1 ==="

python3 -m py_compile \
  src/scripts/research/apply_research_knowledge_base_schema_v1.py

src/scripts/research/apply_research_knowledge_base_schema_v1.py --apply \
  | tee /tmp/research_knowledge_base_schema_apply_v1.out

grep -q "RESEARCH_KNOWLEDGE_BASE_SCHEMA_APPLY_V1" /tmp/research_knowledge_base_schema_apply_v1.out
grep -q "db_update=1" /tmp/research_knowledge_base_schema_apply_v1.out
grep -q "tables_applied=4" /tmp/research_knowledge_base_schema_apply_v1.out
grep -q "indexes_applied=4" /tmp/research_knowledge_base_schema_apply_v1.out
grep -q "runtime_changed=0" /tmp/research_knowledge_base_schema_apply_v1.out
grep -q "execution_changed=0" /tmp/research_knowledge_base_schema_apply_v1.out
grep -q "real_trading_enabled=0" /tmp/research_knowledge_base_schema_apply_v1.out
grep -q "orders_sent=0" /tmp/research_knowledge_base_schema_apply_v1.out
grep -q "VERDICT=RESEARCH_KNOWLEDGE_BASE_SCHEMA_APPLY_OK" /tmp/research_knowledge_base_schema_apply_v1.out

echo "TEST_RESEARCH_KNOWLEDGE_BASE_SCHEMA_APPLY_V1_OK"
