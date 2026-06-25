#!/usr/bin/env python3

# План онтологии состояний рынка.
# Скрипт ничего не меняет в БД, runtime и execution.
# Назначение: зафиксировать единый словарь состояний для Research Platform.

ONTOLOGY = {
    "MARKET_STRUCTURE": {
        "TREND": ["UP_STRONG", "UP", "SIDEWAYS", "DOWN", "DOWN_STRONG", "REVERSAL_UP", "REVERSAL_DOWN", "UNKNOWN"],
        "VOLATILITY": ["VERY_LOW", "LOW", "NORMAL", "HIGH", "EXTREME", "UNKNOWN"],
        "LIQUIDITY": ["VERY_LOW", "LOW", "NORMAL", "HIGH", "EXTREME", "UNKNOWN"],
        "MARKET_PHASE": ["ACCUMULATION", "DISTRIBUTION", "EXPANSION", "CONSOLIDATION", "TRENDING", "UNKNOWN"],
    },
    "PRICE_ACTION": {
        "BREAKOUT": ["NONE", "UP", "DOWN", "FALSE_UP", "FALSE_DOWN", "UNKNOWN"],
        "COMPRESSION": ["NONE", "LIGHT", "MEDIUM", "STRONG", "UNKNOWN"],
        "MOMENTUM": ["STRONG_UP", "UP", "NEUTRAL", "DOWN", "STRONG_DOWN", "UNKNOWN"],
        "MEAN_REVERSION": ["NONE", "WEAK", "MEDIUM", "STRONG", "UNKNOWN"],
    },
    "SESSION": {
        "SESSION_BUCKET": ["ASIA", "EUROPE", "US", "MOSCOW_DAY", "MOSCOW_EVENING", "CLOSED", "UNKNOWN"],
    },
    "DERIVATIVES": {
        "ROLL_PHASE": ["NONE", "PRE_ROLL", "ACTIVE_ROLL", "POST_ROLL", "UNKNOWN"],
        "EXPIRATION": ["NONE", "TODAY", "THIS_WEEK", "NEXT_WEEK", "UNKNOWN"],
    },
    "CALENDAR": {
        "HOLIDAY": ["NONE", "LOCAL", "GLOBAL", "UNKNOWN"],
        "MACRO_EVENT": ["NONE", "CPI", "PPI", "FOMC", "ECB", "BOE", "NFP", "PMI", "OPEC", "GDP", "UNKNOWN"],
    },
    "RISK": {
        "RISK_REGIME": ["LOW", "NORMAL", "HIGH", "PANIC", "UNKNOWN"],
        "NEWS_IMPACT": ["NONE", "LOW", "MEDIUM", "HIGH", "UNKNOWN"],
    },
    "CORRELATION": {
        "INTERMARKET_CONFIRMATION": ["CONFIRMED", "DIVERGENCE", "INVERSE", "UNKNOWN"],
    },
    "MICROSTRUCTURE": {
        "ORDERFLOW": ["BUY", "SELL", "BALANCED", "UNKNOWN"],
        "VOLUME_PROFILE": ["LOW_NODE", "HIGH_NODE", "POC", "UNKNOWN"],
    },
    "EXECUTION_CONTEXT": {
        "SPREAD": ["LOW", "NORMAL", "HIGH", "UNKNOWN"],
        "SLIPPAGE": ["LOW", "NORMAL", "HIGH", "UNKNOWN"],
    },
    "QUALITY": {
        "STATE_CONFIDENCE": ["VERY_LOW", "LOW", "MEDIUM", "HIGH", "VERY_HIGH", "UNKNOWN"],
    },
}

print("=== RESEARCH_MARKET_STATE_ONTOLOGY_PLAN_V1 ===")
print("mode=plan_only")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")

print("\nONTOLOGY_GROUPS")
for domain, groups in ONTOLOGY.items():
    print(f"DOMAIN name={domain} groups={','.join(groups.keys())}")

print("\nONTOLOGY_VALUES")
for domain, groups in ONTOLOGY.items():
    for group, values in groups.items():
        print(
            "STATE_GROUP "
            f"domain={domain} "
            f"group={group} "
            f"values={','.join(values)}"
        )

print("\nDESIGN_RULES")
print("rule=ontology_is_strategy_independent")
print("rule=ontology_is_asset_independent")
print("rule=ontology_is_exchange_independent")
print("rule=ontology_is_broker_independent")
print("rule=all_states_have_stable_codes")
print("rule=unknown_state_is_explicit")
print("rule=new_states_extend_rows_not_columns")
print("rule=research_layer_only")
print("rule=no_runtime_execution_changes")

print("\nNEXT_STEPS")
print("next=RESEARCH_MARKET_STATE_SCHEMA_PLAN_V1")
print("next=RESEARCH_MARKET_STATE_CLASSIFIER_PLAN_V1")
print("next=RESEARCH_STATE_EDGE_SCORECARD_PLAN_V1")

print("\nVERDICT=RESEARCH_MARKET_STATE_ONTOLOGY_PLAN_READY")
