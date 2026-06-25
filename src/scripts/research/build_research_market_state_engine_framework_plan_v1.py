#!/usr/bin/env python3

# ==========================================================
# RESEARCH_MARKET_STATE_ENGINE_FRAMEWORK_PLAN_V1
#
# План фреймворка Market State Engine.
#
# Engine превращает рыночные признаки в Market State Snapshot.
#
# ВАЖНО:
# - только plan_only;
# - БД не изменяется;
# - Runtime не изменяется;
# - Execution не изменяется;
# - Engine не читает PnL;
# - Engine не принимает торговые решения.
# ==========================================================

print("=== RESEARCH_MARKET_STATE_ENGINE_FRAMEWORK_PLAN_V1 ===")
print("mode=plan_only")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")

stages = [
    ("FeatureValidator", 1, "Проверяет полноту и корректность входных рыночных признаков."),
    ("FeatureNormalizer", 2, "Приводит признаки к единому формату для классификаторов."),
    ("ClassifierPipeline", 3, "Запускает независимые классификаторы состояния рынка."),
    ("ConflictResolver", 4, "Выявляет противоречия между результатами классификаторов."),
    ("QualityEvaluator", 5, "Определяет качество состояния рынка: GOOD, WEAK, CONFLICTED, UNKNOWN."),
    ("SnapshotBuilder", 6, "Создает неизменяемый Market State Snapshot."),
    ("SignatureBuilder", 7, "Создает canonical_signature и compact_signature."),
    ("ExplanationBuilder", 8, "Формирует русское дерево объяснения результата."),
]

print("\nENGINE_STAGES")
for code, order, description in stages:
    print(f"ENGINE_STAGE order={order} code={code} description_ru={description}")

print("\nENGINE_OUTPUTS")
outputs = [
    "market_state_snapshot",
    "canonical_signature",
    "compact_signature",
    "market_state_confidence",
    "market_state_quality",
    "conflict_score",
    "explanation_tree_ru",
    "classifier_versions",
    "ontology_version",
    "research_version",
]
for output in outputs:
    print(f"ENGINE_OUTPUT name={output}")

print("\nQUALITY_STATES")
for state in ["GOOD", "WEAK", "CONFLICTED", "UNKNOWN", "INVALID_FEATURE_SET"]:
    print(f"QUALITY_STATE code={state}")

print("\nENGINE_CONTRACTS")
contracts = [
    "engine_accepts_market_features_only",
    "engine_never_reads_pnl",
    "engine_never_reads_trade_result",
    "engine_never_sends_orders",
    "engine_never_changes_runtime",
    "engine_never_changes_execution",
    "engine_never_makes_buy_sell_hold_decision",
    "engine_is_deterministic",
    "engine_is_stateless",
    "snapshots_are_immutable",
    "same_input_same_output",
    "confidence_is_numeric",
    "quality_is_categorical",
    "confidence_is_separate_from_quality",
    "canonical_signature_is_human_readable",
    "compact_signature_is_hash_or_short_code",
    "explanation_tree_ru_is_required",
]
for contract in contracts:
    print(f"contract={contract}")

print("\nDESIGN_RULES")
rules = [
    "market_state_engine_is_research_only",
    "feature_validation_before_classification",
    "feature_normalization_before_classifier_pipeline",
    "classification_before_conflict_resolution",
    "conflict_score_is_numeric",
    "quality_is_categorical",
    "confidence_is_numeric",
    "snapshot_builder_requires_versions",
    "signature_builder_requires_canonical_signature",
    "signature_builder_requires_compact_signature",
    "explanation_builder_requires_ru_output",
    "edge_discovery_starts_after_engine",
    "no_runtime_execution_changes",
]
for rule in rules:
    print(f"rule={rule}")

print("\nFILE_STRUCTURE")
print("file=src/scripts/research/build_research_market_state_engine_framework_plan_v1.py")
print("file=scripts/test_research_market_state_engine_framework_plan_v1.sh")

print("\nNEXT_STEPS")
print("next=RESEARCH_MARKET_STATE_EDGE_DISCOVERY_ENGINE_PLAN_V1")
print("next=RESEARCH_STRATEGY_RECOMMENDATION_ENGINE_PLAN_V1")
print("next=MICRO_LIVE_PREPARATION_V1")

print("\nVERDICT=RESEARCH_MARKET_STATE_ENGINE_FRAMEWORK_PLAN_READY")
