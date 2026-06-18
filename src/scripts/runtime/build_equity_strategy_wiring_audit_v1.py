#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


# Русский комментарий:
# EQUITY_STRATEGY_WIRING_AUDIT_V1 — read-only файловый аудит wiring.
# Ничего не меняет в коде, БД, runtime, systemd и execution.
# Цель — проверить, совпадает ли runtime strategy VOLATILITY_BREAKOUT_EQUITY
# с тем, что реально подключено в paper_pipeline.


ROOT = Path(".")
TARGET_FILES = [
    Path("src/finam_core/pipelines/paper_pipeline.py"),
    Path("src/finam_core/strategy/strategy_factory.py"),
    Path("src/finam_core/strategy/symbol_strategy_map.py"),
    Path("src/finam_core/strategy/equities/volatility_breakout_equity.py"),
    Path("src/finam_core/strategy/equities/mean_reversion_equity.py"),
    Path("src/scripts/update_dynamic_watchlist_from_opportunities.py"),
    Path("src/finam_core/data/moex_opportunity_scanner.py"),
]


PATTERNS = {
    "volatility_breakout_name": "VOLATILITY_BREAKOUT_EQUITY",
    "mean_reversion_name": "MEAN_REVERSION_EQUITY",
    "strategy_factory": "StrategyFactory",
    "create_strategy": "create_strategy",
    "volatility_class": "VolatilityBreakoutEquity",
    "mean_reversion_class": "MeanReversion",
    "legacy_mean_reversion": "self.mean_reversion",
    "runtime_active_universe": "runtime_active_universe",
    "runtime_provider": "RuntimeUniverseProvider",
    "runtime_gate": "_runtime_active_universe_allows_paper",
    "misx": "@MISX",
}


def read_file(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(errors="ignore")


def count_occurrences(text: str, pattern: str) -> int:
    return text.count(pattern)


def find_lines(path: Path, patterns: dict[str, str]) -> list[tuple[int, str, str]]:
    if not path.exists():
        return []

    rows: list[tuple[int, str, str]] = []

    for lineno, line in enumerate(path.read_text(errors="ignore").splitlines(), 1):
        for key, pattern in patterns.items():
            if pattern in line:
                rows.append((lineno, key, line.strip()))

    return rows


def main() -> int:
    print("=== EQUITY STRATEGY WIRING AUDIT V1 ===")
    print("mode=read_only")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print("db_update=0")
    print()

    paper = read_file(Path("src/finam_core/pipelines/paper_pipeline.py"))
    factory = read_file(Path("src/finam_core/strategy/strategy_factory.py"))
    symbol_map = read_file(Path("src/finam_core/strategy/symbol_strategy_map.py"))
    volatility = read_file(Path("src/finam_core/strategy/equities/volatility_breakout_equity.py"))
    meanrev = read_file(Path("src/finam_core/strategy/equities/mean_reversion_equity.py"))

    print("EQUITY_STRATEGY_WIRING_FILE_ROWS")
    for path in TARGET_FILES:
        exists = path.exists()
        size = path.stat().st_size if exists else 0
        print(
            "EQUITY_STRATEGY_WIRING_FILE_ROW "
            f"path={path} "
            f"exists={1 if exists else 0} "
            f"size={size}"
        )

    print()
    print("EQUITY_STRATEGY_WIRING_PATTERN_ROWS")
    for path in TARGET_FILES:
        text = read_file(path)
        for key, pattern in PATTERNS.items():
            cnt = count_occurrences(text, pattern)
            if cnt:
                print(
                    "EQUITY_STRATEGY_WIRING_PATTERN_ROW "
                    f"path={path} "
                    f"pattern_key={key} "
                    f"pattern={pattern} "
                    f"count={cnt}"
                )

    print()
    print("EQUITY_STRATEGY_WIRING_MATCH_LINES")
    for path in TARGET_FILES:
        for lineno, key, line in find_lines(path, PATTERNS):
            print(
                "EQUITY_STRATEGY_WIRING_MATCH_LINE "
                f"path={path} "
                f"lineno={lineno} "
                f"pattern_key={key} "
                f"line=\"{line}\""
            )

    factory_supports_volatility = (
        "VOLATILITY_BREAKOUT_EQUITY" in factory
        and "VolatilityBreakoutEquity" in factory
    )
    volatility_class_exists = "class VolatilityBreakoutEquity" in volatility
    meanrev_class_exists = "class MeanReversion" in meanrev or "class MeanReversionEquity" in meanrev

    paper_imports_factory = "strategy_factory" in paper or "StrategyFactory" in paper
    paper_imports_volatility = "VolatilityBreakoutEquity" in paper or "volatility_breakout_equity" in paper
    paper_uses_volatility_name = "VOLATILITY_BREAKOUT_EQUITY" in paper
    paper_uses_mean_reversion = "MeanReversionStrategy" in paper or "self.mean_reversion" in paper

    symbol_map_defaults_mean_reversion = "DEFAULT_STRATEGY = \"MEAN_REVERSION_EQUITY\"" in symbol_map
    symbol_map_has_volatility = "VOLATILITY_BREAKOUT_EQUITY" in symbol_map

    # Русский комментарий:
    # Ключевой критерий mismatch:
    # factory знает volatility breakout, но paper_pipeline не использует factory/volatility,
    # зато использует legacy mean_reversion.
    wiring_mismatch = (
        factory_supports_volatility
        and volatility_class_exists
        and not paper_imports_volatility
        and not paper_uses_volatility_name
        and paper_uses_mean_reversion
    )

    symbol_map_legacy_bias = symbol_map_defaults_mean_reversion and not symbol_map_has_volatility

    print()
    print("EQUITY_STRATEGY_WIRING_AUDIT_SUMMARY")
    print(f"factory_supports_volatility={1 if factory_supports_volatility else 0}")
    print(f"volatility_class_exists={1 if volatility_class_exists else 0}")
    print(f"mean_reversion_class_exists={1 if meanrev_class_exists else 0}")
    print(f"paper_imports_strategy_factory={1 if paper_imports_factory else 0}")
    print(f"paper_imports_volatility={1 if paper_imports_volatility else 0}")
    print(f"paper_uses_volatility_name={1 if paper_uses_volatility_name else 0}")
    print(f"paper_uses_mean_reversion={1 if paper_uses_mean_reversion else 0}")
    print(f"symbol_map_defaults_mean_reversion={1 if symbol_map_defaults_mean_reversion else 0}")
    print(f"symbol_map_has_volatility={1 if symbol_map_has_volatility else 0}")
    print(f"symbol_map_legacy_bias={1 if symbol_map_legacy_bias else 0}")
    print(f"wiring_mismatch={1 if wiring_mismatch else 0}")
    print("db_update=0")

    if wiring_mismatch:
        print("VERDICT=EQUITY_STRATEGY_WIRING_MISMATCH_CONFIRMED")
    elif factory_supports_volatility and paper_imports_volatility:
        print("VERDICT=EQUITY_STRATEGY_WIRING_PARTIALLY_WIRED")
    else:
        print("VERDICT=EQUITY_STRATEGY_WIRING_NEEDS_MANUAL_REVIEW")

    print("EQUITY_STRATEGY_WIRING_AUDIT_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
