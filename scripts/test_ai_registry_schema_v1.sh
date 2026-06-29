#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_AI_REGISTRY_SCHEMA_V1 ==="

PYTHONPATH=src src/scripts/research/build_ai_registry_schema_v1.py \
  | tee /tmp/ai_registry_schema_v1.out

grep -q "AI_REGISTRY_SCHEMA_V1" /tmp/ai_registry_schema_v1.out
grep -q "table=warehouse.ai_registry_v1" /tmp/ai_registry_schema_v1.out
grep -q "назначение=реестр_AI_компонентов_платформы" /tmp/ai_registry_schema_v1.out
grep -q "ai_types=AI_AGENT,AI_PROMPT,AI_POLICY,AI_PIPELINE,AI_WORKFLOW,AI_CAPABILITY,AI_EVALUATION,AI_TEMPLATE" /tmp/ai_registry_schema_v1.out
grep -q "status_model=DISCOVERED,REGISTERED,VALIDATED,APPROVED,DEPRECATED,ARCHIVED" /tmp/ai_registry_schema_v1.out
grep -q "maturity_model=RESEARCH,VALIDATED,SHADOW,PAPER,LIVE" /tmp/ai_registry_schema_v1.out
grep -q "execution_policy=AI_RECOMMENDS_ONLY_NO_DIRECT_EXECUTION" /tmp/ai_registry_schema_v1.out
grep -q "market_knowledge_policy=AI_REGISTRY_STORES_AI_KNOWLEDGE_ONLY" /tmp/ai_registry_schema_v1.out
grep -q "source_policy=AI_REGISTRY_DOES_NOT_STORE_MARKET_KNOWLEDGE" /tmp/ai_registry_schema_v1.out
grep -q "framework=REGISTRY_FRAMEWORK_V1" /tmp/ai_registry_schema_v1.out
grep -q "runtime_changed=0" /tmp/ai_registry_schema_v1.out
grep -q "execution_changed=0" /tmp/ai_registry_schema_v1.out
grep -q "orders_changed=0" /tmp/ai_registry_schema_v1.out
grep -q "fills_changed=0" /tmp/ai_registry_schema_v1.out
grep -q "micro_live_allowed=0" /tmp/ai_registry_schema_v1.out
grep -q "VERDICT=AI_REGISTRY_SCHEMA_V1_READY" /tmp/ai_registry_schema_v1.out
grep -q "ai_registry_exists=true" /tmp/ai_registry_schema_v1.out

psql "${DATABASE_URL:-postgresql:///finam_core}" -At <<'SQL' | tee /tmp/ai_registry_schema_columns_v1.out
SELECT 'forbidden_feature_code=' || EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='warehouse'
      AND table_name='ai_registry_v1'
      AND column_name='feature_code'
);

SELECT 'forbidden_model_code=' || EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='warehouse'
      AND table_name='ai_registry_v1'
      AND column_name='model_code'
);

SELECT 'forbidden_experiment_code=' || EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='warehouse'
      AND table_name='ai_registry_v1'
      AND column_name='experiment_code'
);

SELECT 'forbidden_dataset_code=' || EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema='warehouse'
      AND table_name='ai_registry_v1'
      AND column_name='dataset_code'
);
SQL

grep -q "forbidden_feature_code=false" /tmp/ai_registry_schema_columns_v1.out
grep -q "forbidden_model_code=false" /tmp/ai_registry_schema_columns_v1.out
grep -q "forbidden_experiment_code=false" /tmp/ai_registry_schema_columns_v1.out
grep -q "forbidden_dataset_code=false" /tmp/ai_registry_schema_columns_v1.out

echo "TEST_AI_REGISTRY_SCHEMA_V1_OK"
