#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path

print("=== EQUITY_STRATEGY_NAME_RESOLVER_PATCH_PLAN_V1 ===")
print("mode=read_only_plan")
print("db_update=0")
print("runtime_changed=0")
print("execution_changed=0")
print("real_trading_enabled=0")

paper = Path("src/finam_core/pipelines/paper_pipeline.py")
symbol_map = Path("src/finam_core/strategy/symbol_strategy_map.py")

paper_text = paper.read_text(errors="ignore")
map_text = symbol_map.read_text(errors="ignore")

runtime_resolver_present = "_runtime_strategy_name_for_symbol" in paper_text
legacy_resolver_present = "_strategy_name_for_symbol" in paper_text

default_mean_present = 'DEFAULT_STRATEGY = "MEAN_REVERSION_EQUITY"' in map_text

misx_runtime_calls = paper_text.count("_runtime_strategy_name_for_symbol(")
legacy_calls = paper_text.count("_strategy_name_for_symbol(")

print(
    f"runtime_resolver_present={int(runtime_resolver_present)}"
)
print(
    f"legacy_resolver_present={int(legacy_resolver_present)}"
)
print(
    f"default_mean_present={int(default_mean_present)}"
)
print(
    f"misx_runtime_calls={misx_runtime_calls}"
)
print(
    f"legacy_calls={legacy_calls}"
)

print("PATCH_STEP_1")
print(
    "Для @MISX использовать runtime_active_universe.strategy "
    "до любого обращения к symbol_strategy_map."
)

print("PATCH_STEP_2")
print(
    "Сохранить fallback на symbol_strategy_map только "
    "если runtime_active_universe не содержит строку."
)

print("PATCH_STEP_3")
print(
    "Не изменять BR/NG/USDRUB/FUTURES маршруты."
)

print("PATCH_STEP_4")
print(
    "После патча выполнить fresh mismatch audit."
)

print("decision=PREPARE_PATCH")

print("VERDICT=EQUITY_STRATEGY_NAME_RESOLVER_PATCH_PLAN_READY")
print("TEST_EQUITY_STRATEGY_NAME_RESOLVER_PATCH_PLAN_V1_OK")
