#!/usr/bin/env python3

# ==========================================================
# RESEARCH_MARKET_STATE_SCHEMA_PLAN_V1
#
# План канонической схемы хранения состояний рынка.
#
# ВАЖНО:
# - Только исследовательский слой.
# - Никаких изменений Runtime.
# - Никаких изменений Execution.
# - Только архитектурный план.
# ==========================================================

print("=== RESEARCH_MARKET_STATE_SCHEMA_PLAN_V1 ===")
print("mode=plan_only")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")

tables = {

    "research.market_state_domains_v1": [
        "domain_id",
        "domain_code",
        "domain_name",
        "description_ru",
        "is_active"
    ],

    "research.market_state_groups_v1": [
        "group_id",
        "domain_id",
        "group_code",
        "group_name",
        "description_ru",
        "sort_order",
        "is_active"
    ],

    "research.market_state_catalog_v1": [
        "state_id",
        "group_id",
        "state_code",
        "state_name",
        "description_ru",
        "severity",
        "sort_order",
        "is_default",
        "is_active"
    ],

    "research.market_state_glossary_v1": [
        "glossary_id",
        "state_id",
        "language",
        "term",
        "short_name",
        "definition",
        "research_definition",
        "trading_interpretation",
        "examples",
        "notes",
        "version"
    ],

    "research.market_state_algorithms_v1": [
        "algorithm_id",
        "algorithm_code",
        "algorithm_name",
        "description_ru",
        "implementation",
        "version",
        "is_active"
    ],

    "research.market_state_classifier_versions_v1": [
        "classifier_version_id",
        "classifier_name",
        "version",
        "description_ru",
        "created_at",
        "is_active"
    ],

    "research.market_state_algorithm_mapping_v1": [
        "mapping_id",
        "state_id",
        "algorithm_id",
        "classifier_version_id",
        "valid_from",
        "valid_to"
    ],

    "research.market_state_snapshots_v1": [
        "snapshot_id",
        "snapshot_ts",
        "symbol",
        "asset_class",
        "timeframe",
        "quality",
        "source",
        "created_at"
    ],

    "research.market_state_snapshot_metadata_v1": [
        "snapshot_id",
        "classifier_version_id",
        "ontology_version",
        "research_version",
        "created_by",
        "created_at"
    ],

    "research.market_state_snapshot_values_v1": [
        "snapshot_value_id",
        "snapshot_id",
        "group_id",
        "state_id",
        "confidence",
        "source"
    ],

    "research.trade_state_snapshots_v1": [
        "trade_id",
        "entry_snapshot_id",
        "exit_snapshot_id",
        "holding_snapshot_count"
    ],

    "research.market_state_transitions_v1": [
        "transition_id",
        "symbol",
        "snapshot_from",
        "snapshot_to",
        "transition_type",
        "duration_seconds"
    ],

    "research.state_edge_scorecards_v1": [
        "state_key",
        "trades",
        "wins",
        "losses",
        "gross_pnl",
        "net_pnl",
        "profit_factor",
        "expectancy",
        "mae",
        "mfe",
        "holding"
    ],

    "research.strategy_state_matrix_v1": [
        "strategy",
        "state_key",
        "trades",
        "expectancy",
        "profit_factor",
        "net_pnl"
    ],

    "research.research_hypotheses_v1": [
        "hypothesis_id",
        "code",
        "title_ru",
        "status"
    ],

    "research.research_experiments_v1": [
        "experiment_id",
        "hypothesis_id",
        "algorithm_version",
        "dataset",
        "result"
    ],

    "research.research_decisions_v1": [
        "decision_id",
        "experiment_id",
        "decision",
        "reason",
        "created_at"
    ]

}

print("\nTABLES")

for table, cols in tables.items():
    print(f"TABLE name={table} columns={','.join(cols)}")

print("\nDESIGN_RULES")

rules = [
    "ontology_is_single_source_of_truth",
    "fully_normalized",
    "all_state_values_are_rows",
    "all_terms_have_glossary",
    "multilanguage_ready",
    "all_states_have_algorithm",
    "classifier_versions_are_tracked",
    "snapshot_metadata_is_immutable",
    "trade_links_to_snapshots",
    "edge_calculated_from_market_states",
    "research_governance_ready",
    "no_runtime_execution_changes",
    "no_table_without_business_purpose"
]

for r in rules:
    print(f"rule={r}")

print("\nVERDICT=RESEARCH_MARKET_STATE_SCHEMA_PLAN_READY")
