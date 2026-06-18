#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


# Русский комментарий:
# EQUITY_STRATEGY_WIRING_PATCH_PLAN_V1 — read-only план исправления wiring.
# Скрипт не меняет файлы, БД, runtime, systemd и execution.
# Цель — формально зафиксировать безопасный план патча:
# equity path должен брать strategy из runtime_active_universe
# и создавать strategy через StrategyFactory, не ломая NG/BR/USDRUB.


PAPER_PIPELINE = Path("src/finam_core/pipelines/paper_pipeline.py")
STRATEGY_FACTORY = Path("src/finam_core/strategy/strategy_factory.py")
VOLATILITY_STRATEGY = Path("src/finam_core/strategy/equities/volatility_breakout_equity.py")
MEAN_REVERSION_LEGACY = Path("src/finam_core/strategy/mean_reversion.py")
SYMBOL_STRATEGY_MAP = Path("src/finam_core/strategy/symbol_strategy_map.py")


def read(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(errors="ignore")


def line_hits(path: Path, patterns: tuple[str, ...]) -> list[tuple[int, str]]:
    if not path.exists():
        return []

    rows: list[tuple[int, str]] = []
    for lineno, line in enumerate(path.read_text(errors="ignore").splitlines(), 1):
        if any(p in line for p in patterns):
            rows.append((lineno, line.strip()))
    return rows


def main() -> int:
    paper = read(PAPER_PIPELINE)
    factory = read(STRATEGY_FACTORY)
    volatility = read(VOLATILITY_STRATEGY)
    legacy_mean = read(MEAN_REVERSION_LEGACY)
    symbol_map = read(SYMBOL_STRATEGY_MAP)

    factory_supports_volatility = (
        "VOLATILITY_BREAKOUT_EQUITY" in factory
        and "VolatilityBreakoutEquity" in factory
    )
    volatility_class_exists = "class VolatilityBreakoutEquity" in volatility
    paper_uses_factory = "StrategyFactory" in paper
    paper_uses_volatility = (
        "VOLATILITY_BREAKOUT_EQUITY" in paper
        or "VolatilityBreakoutEquity" in paper
        or "volatility_breakout_equity" in paper
    )
    paper_uses_legacy_mean = (
        "MeanReversionStrategy" in paper
        or "self.mean_reversion" in paper
    )
    symbol_map_defaults_mean = 'DEFAULT_STRATEGY = "MEAN_REVERSION_EQUITY"' in symbol_map
    legacy_mean_exists = "class MeanReversionStrategy" in legacy_mean

    needs_patch = (
        factory_supports_volatility
        and volatility_class_exists
        and paper_uses_factory
        and not paper_uses_volatility
        and paper_uses_legacy_mean
    )

    print("=== EQUITY STRATEGY WIRING PATCH PLAN V1 ===")
    print("mode=read_only")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print("db_update=0")
    print("file_update=0")
    print()

    print("EQUITY_STRATEGY_WIRING_PATCH_PLAN_INPUTS")
    print(f"factory_supports_volatility={1 if factory_supports_volatility else 0}")
    print(f"volatility_class_exists={1 if volatility_class_exists else 0}")
    print(f"paper_uses_strategy_factory={1 if paper_uses_factory else 0}")
    print(f"paper_uses_volatility={1 if paper_uses_volatility else 0}")
    print(f"paper_uses_legacy_mean_reversion={1 if paper_uses_legacy_mean else 0}")
    print(f"legacy_mean_reversion_exists={1 if legacy_mean_exists else 0}")
    print(f"symbol_map_defaults_mean_reversion={1 if symbol_map_defaults_mean else 0}")
    print(f"needs_patch={1 if needs_patch else 0}")
    print()

    print("EQUITY_STRATEGY_WIRING_PATCH_PLAN_LINES")
    for lineno, line in line_hits(
        PAPER_PIPELINE,
        (
            "StrategyFactory",
            "MeanReversionStrategy",
            "self.mean_reversion",
            "_runtime_active_universe_allows_paper",
            "runtime_active_universe",
        ),
    ):
        print(
            "EQUITY_STRATEGY_WIRING_PATCH_PLAN_LINE "
            f"path={PAPER_PIPELINE} "
            f"lineno={lineno} "
            f"line=\"{line}\""
        )

    print()
    print("EQUITY_STRATEGY_WIRING_PATCH_PLAN_STEPS")
    steps = [
        (
            1,
            "add_equity_strategy_resolver",
            "Добавить helper в paper_pipeline: получить active_strategy из runtime_active_universe для equity symbol.",
            "read_only_or_soft_fail",
        ),
        (
            2,
            "use_strategy_factory_for_equities",
            "Для @MISX создавать strategy через StrategyFactory.create(active_strategy), а не через legacy self.mean_reversion.",
            "paper_only",
        ),
        (
            3,
            "preserve_futures_paths",
            "Не менять NG/BR/USDRUB flows, _ng_strategy_for_symbol и futures gates.",
            "required",
        ),
        (
            4,
            "preserve_execution_disabled",
            "Не включать real execution; все проверки остаются runtime_allow=0/execution_enabled=0.",
            "required",
        ),
        (
            5,
            "add_dry_run_invocation_test",
            "Добавить bash-only test: SBER@MISX runtime strategy resolves to VOLATILITY_BREAKOUT_EQUITY.",
            "required",
        ),
        (
            6,
            "add_trace_validation",
            "После патча прогнать trace: expected_strategy_guard_count должен стать >0 или появиться signals/intents.",
            "required",
        ),
    ]

    for order, code, description, safety in steps:
        print(
            "EQUITY_STRATEGY_WIRING_PATCH_PLAN_STEP "
            f"order={order} "
            f"code={code} "
            f"safety={safety} "
            f"description=\"{description}\""
        )

    print()
    print("EQUITY_STRATEGY_WIRING_PATCH_PLAN_GUARDS")
    guards = [
        "do_not_touch_futures_execution",
        "do_not_enable_real_trading",
        "do_not_change_runtime_active_universe_data",
        "do_not_change_research_decision_state",
        "do_not_rewrite_paper_pipeline_broadly",
        "patch_only_equity_strategy_resolution_path",
    ]
    for guard in guards:
        print(f"EQUITY_STRATEGY_WIRING_PATCH_PLAN_GUARD name={guard} status=REQUIRED")

    print()
    print("EQUITY_STRATEGY_WIRING_PATCH_PLAN_SUMMARY")
    print(f"needs_patch={1 if needs_patch else 0}")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print("db_update=0")
    print("file_update=0")

    if needs_patch:
        print("decision=PREPARE_EQUITY_STRATEGY_WIRING_PATCH")
        print("VERDICT=EQUITY_STRATEGY_WIRING_PATCH_PLAN_READY")
    else:
        print("decision=NO_PATCH_PLAN_OR_MANUAL_REVIEW")
        print("VERDICT=EQUITY_STRATEGY_WIRING_PATCH_PLAN_NEEDS_REVIEW")

    print("EQUITY_STRATEGY_WIRING_PATCH_PLAN_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
