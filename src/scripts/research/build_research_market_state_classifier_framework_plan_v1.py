#!/usr/bin/env python3

# ==========================================================
# RESEARCH_MARKET_STATE_CLASSIFIER_FRAMEWORK_PLAN_V1
#
# План фреймворка классификаторов рыночного состояния.
#
# ВАЖНО:
# - Только исследовательский слой.
# - Никаких изменений Runtime.
# - Никаких изменений Execution.
# - Классификаторы не используют PnL и не знают результат сделки.
# ==========================================================

print("=== RESEARCH_MARKET_STATE_CLASSIFIER_FRAMEWORK_PLAN_V1 ===")
print("mode=plan_only")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")

classifiers = [
    {
        "classifier_code": "TrendClassifierV1",
        "classifier_name": "Классификатор тренда",
        "input_features": "ohlc,ema,adx,price_structure",
        "output_group": "TREND",
        "output_states": "UP_STRONG,UP,SIDEWAYS,DOWN,DOWN_STRONG,REVERSAL_UP,REVERSAL_DOWN,UNKNOWN",
        "confidence_method": "SCORE",
        "research_status": "RESEARCH",
    },
    {
        "classifier_code": "VolatilityClassifierV1",
        "classifier_name": "Классификатор волатильности",
        "input_features": "atr_pct,range_pct,realized_volatility",
        "output_group": "VOLATILITY",
        "output_states": "VERY_LOW,LOW,NORMAL,HIGH,EXTREME,UNKNOWN",
        "confidence_method": "STATIC_RULE",
        "research_status": "RESEARCH",
    },
    {
        "classifier_code": "LiquidityClassifierV1",
        "classifier_name": "Классификатор ликвидности",
        "input_features": "volume,avg_volume,spread,turnover",
        "output_group": "LIQUIDITY",
        "output_states": "VERY_LOW,LOW,NORMAL,HIGH,EXTREME,UNKNOWN",
        "confidence_method": "SCORE",
        "research_status": "RESEARCH",
    },
    {
        "classifier_code": "CompressionClassifierV1",
        "classifier_name": "Классификатор сжатия",
        "input_features": "range_pct,atr_pct,compression_ratio",
        "output_group": "COMPRESSION",
        "output_states": "NONE,LIGHT,MEDIUM,STRONG,UNKNOWN",
        "confidence_method": "STATIC_RULE",
        "research_status": "RESEARCH",
    },
    {
        "classifier_code": "BreakoutClassifierV1",
        "classifier_name": "Классификатор пробоя",
        "input_features": "close,prev_high,prev_low,breakout_distance_pct,return_inside_range",
        "output_group": "BREAKOUT",
        "output_states": "NONE,UP,DOWN,FALSE_UP,FALSE_DOWN,UNKNOWN",
        "confidence_method": "SCORE",
        "research_status": "RESEARCH",
    },
    {
        "classifier_code": "MomentumClassifierV1",
        "classifier_name": "Классификатор импульса",
        "input_features": "momentum_1,momentum_3,roc,bar_body_pct",
        "output_group": "MOMENTUM",
        "output_states": "STRONG_UP,UP,NEUTRAL,DOWN,STRONG_DOWN,UNKNOWN",
        "confidence_method": "SCORE",
        "research_status": "RESEARCH",
    },
    {
        "classifier_code": "MeanReversionClassifierV1",
        "classifier_name": "Классификатор возврата к среднему",
        "input_features": "distance_to_ma,z_score,rsi,band_position",
        "output_group": "MEAN_REVERSION",
        "output_states": "NONE,WEAK,MEDIUM,STRONG,UNKNOWN",
        "confidence_method": "SCORE",
        "research_status": "RESEARCH",
    },
    {
        "classifier_code": "SessionClassifierV1",
        "classifier_name": "Классификатор торговой сессии",
        "input_features": "timestamp,exchange_calendar,timezone",
        "output_group": "SESSION_BUCKET",
        "output_states": "ASIA,EUROPE,US,MOSCOW_DAY,MOSCOW_EVENING,CLOSED,UNKNOWN",
        "confidence_method": "STATIC_RULE",
        "research_status": "RESEARCH",
    },
    {
        "classifier_code": "ExpirationClassifierV1",
        "classifier_name": "Классификатор экспирации",
        "input_features": "symbol,expiration_date,trade_date",
        "output_group": "EXPIRATION",
        "output_states": "NONE,TODAY,THIS_WEEK,NEXT_WEEK,UNKNOWN",
        "confidence_method": "STATIC_RULE",
        "research_status": "RESEARCH",
    },
    {
        "classifier_code": "RollPhaseClassifierV1",
        "classifier_name": "Классификатор фазы роллирования",
        "input_features": "contract_code,expiration_date,volume_shift,open_interest_shift",
        "output_group": "ROLL_PHASE",
        "output_states": "NONE,PRE_ROLL,ACTIVE_ROLL,POST_ROLL,UNKNOWN",
        "confidence_method": "SCORE",
        "research_status": "RESEARCH",
    },
    {
        "classifier_code": "MacroEventClassifierV1",
        "classifier_name": "Классификатор макрособытий",
        "input_features": "event_calendar,event_type,event_time,impact_level",
        "output_group": "MACRO_EVENT",
        "output_states": "NONE,CPI,PPI,FOMC,ECB,BOE,NFP,PMI,OPEC,GDP,UNKNOWN",
        "confidence_method": "STATIC_RULE",
        "research_status": "RESEARCH",
    },
    {
        "classifier_code": "RiskRegimeClassifierV1",
        "classifier_name": "Классификатор рыночного риска",
        "input_features": "volatility,drawdown,correlation_stress,news_impact",
        "output_group": "RISK_REGIME",
        "output_states": "LOW,NORMAL,HIGH,PANIC,UNKNOWN",
        "confidence_method": "HYBRID",
        "research_status": "RESEARCH",
    },
    {
        "classifier_code": "CorrelationClassifierV1",
        "classifier_name": "Классификатор межрыночного подтверждения",
        "input_features": "primary_symbol,reference_symbol,rolling_correlation,divergence_pct",
        "output_group": "INTERMARKET_CONFIRMATION",
        "output_states": "CONFIRMED,DIVERGENCE,INVERSE,UNKNOWN",
        "confidence_method": "SCORE",
        "research_status": "RESEARCH",
    },
]

print("\nCLASSIFIERS")
for item in classifiers:
    print(
        "CLASSIFIER "
        f"code={item['classifier_code']} "
        f"name_ru={item['classifier_name']} "
        f"input_features={item['input_features']} "
        f"output_group={item['output_group']} "
        f"output_states={item['output_states']} "
        f"confidence_method={item['confidence_method']} "
        f"research_status={item['research_status']}"
    )

print("\nFRAMEWORK_CONTRACT")
print("contract=classifier_accepts_market_features_only")
print("contract=classifier_returns_state_code")
print("contract=classifier_returns_confidence")
print("contract=classifier_returns_explanation_ru")
print("contract=classifier_returns_algorithm_version")
print("contract=classifier_is_edge_blind")
print("contract=classifier_is_pnl_blind")
print("contract=classifier_is_independent_by_default")

print("\nDESIGN_RULES")
print("rule=classifier_framework_is_research_only")
print("rule=no_classifier_reads_pnl")
print("rule=no_classifier_reads_trade_result")
print("rule=no_classifier_changes_runtime")
print("rule=no_classifier_sends_orders")
print("rule=rule_based_before_ml")
print("rule=all_outputs_match_market_state_ontology")
print("rule=all_classifiers_have_ru_description")
print("rule=all_classifiers_have_confidence_method")
print("rule=all_classifiers_have_explainability")
print("rule=no_runtime_execution_changes")

print("\nNEXT_STEPS")
print("next=RESEARCH_MARKET_STATE_GENERATOR_PLAN_V1")
print("next=RESEARCH_MARKET_STATE_TRANSITION_ENGINE_PLAN_V1")
print("next=RESEARCH_STATE_EDGE_DISCOVERY_PLAN_V1")

print("\nVERDICT=RESEARCH_MARKET_STATE_CLASSIFIER_FRAMEWORK_PLAN_READY")
