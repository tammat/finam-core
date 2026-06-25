#!/usr/bin/env python3

# ==========================================================
# MICRO_LIVE_PREPARATION_V1
#
# План подготовки первого безопасного Micro Live.
#
# ВАЖНО:
# - это НЕ включение реальной торговли;
# - реальные заявки не отправляются;
# - Runtime не изменяется;
# - Execution не изменяется;
# - этап только фиксирует критерии допуска.
# ==========================================================

print("=== MICRO_LIVE_PREPARATION_V1 ===")
print("mode=preparation_plan_only")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")
print("orders_sent=0")

gates = [
    ("ARCHITECTURE_CONSTITUTION_LOCKED", "PASS", "Архитектурная Конституция проекта зафиксирована."),
    ("TRADING_CORE_FREEZE", "PASS", "Trading Core остается в режиме Freeze."),
    ("RESEARCH_PIPELINE_READY", "PASS", "Research Platform имеет ontology/schema/classifier/engine/edge/recommendation планы."),
    ("EDGE_CANDIDATE_REQUIRED", "BLOCKING", "Micro Live невозможен без подтвержденного edge-кандидата."),
    ("RISK_ENGINE_REQUIRED", "BLOCKING", "Risk Engine должен быть активен и проверен перед Micro Live."),
    ("KILL_SWITCH_REQUIRED", "BLOCKING", "Kill Switch должен быть проверен перед Micro Live."),
    ("REAL_EXECUTION_GUARD_REQUIRED", "BLOCKING", "Real execution должен иметь отдельный guard и ручной/управляемый допуск."),
    ("POSITION_SIZE_LIMIT_REQUIRED", "BLOCKING", "Размер позиции должен быть минимальным: micro-size."),
    ("DAILY_LOSS_LIMIT_REQUIRED", "BLOCKING", "Дневной лимит убытка должен быть установлен до запуска."),
    ("AUDIT_LOG_REQUIRED", "BLOCKING", "Все решения, сигналы, отказы, заявки и исполнения должны логироваться."),
    ("ROLLBACK_PLAN_REQUIRED", "BLOCKING", "Должен быть готов план немедленного отключения Micro Live."),
]

print("\nMICRO_LIVE_GATES")
for code, status, description in gates:
    print(f"GATE code={code} status={status} description_ru={description}")

limits = [
    ("max_position_size", "micro_only"),
    ("max_active_instruments", "1"),
    ("max_active_strategy", "1"),
    ("execution_mode", "real_guarded_only"),
    ("risk_mode", "strict"),
    ("kill_switch", "required"),
    ("manual_approval", "required_until_first_validation"),
]

print("\nMICRO_LIVE_LIMITS")
for name, value in limits:
    print(f"LIMIT name={name} value={value}")

required_evidence = [
    "state_edge_scorecard_positive",
    "profit_factor_above_threshold",
    "expectancy_positive_after_commission",
    "sample_size_guard_passed",
    "bias_guard_passed",
    "shadow_validation_passed",
    "paper_validation_passed",
    "risk_fit_passed",
    "execution_fit_passed",
]

print("\nREQUIRED_EVIDENCE")
for item in required_evidence:
    print(f"EVIDENCE name={item}")

contracts = [
    "micro_live_is_not_production",
    "micro_live_requires_edge_candidate",
    "micro_live_requires_separate_approval",
    "micro_live_cannot_be_enabled_by_research_script",
    "micro_live_must_be_reversible",
    "micro_live_must_be_auditable",
    "micro_live_must_start_with_minimal_size",
]

print("\nMICRO_LIVE_CONTRACTS")
for contract in contracts:
    print(f"contract={contract}")

print("\nDESIGN_RULES")
print("rule=money_first")
print("rule=data_first")
print("rule=no_real_trading_without_edge")
print("rule=no_runtime_execution_changes")
print("rule=research_can_recommend_but_cannot_enable_runtime")
print("rule=micro_live_is_guarded_experiment")
print("rule=first_goal_is_safe_real_market_validation_not_profit_maximization")

print("\nBLOCKERS")
print("blocker=NO_CONFIRMED_EDGE_CANDIDATE_YET")
print("blocker=RISK_AND_KILL_SWITCH_VALIDATION_REQUIRED")
print("blocker=REAL_EXECUTION_GUARD_VALIDATION_REQUIRED")

print("\nNEXT_STEPS")
print("next=MICRO_LIVE_GATE_AUDIT_V1")
print("next=EDGE_CANDIDATE_SELECTION_FOR_MICRO_LIVE_V1")

print("\nVERDICT=MICRO_LIVE_PREPARATION_PLAN_READY_NOT_ENABLED")
