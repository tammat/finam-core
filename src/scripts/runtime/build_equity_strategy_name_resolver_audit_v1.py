#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


# Русский комментарий:
# EQUITY_STRATEGY_NAME_RESOLVER_AUDIT_V1 — read-only аудит resolver-а стратегии.
# Ничего не меняет в paper_pipeline.py, БД, runtime, systemd и execution.
# Цель — доказать, что _strategy_name_for_symbol берёт legacy mapping,
# а не runtime_active_universe.strategy.


PAPER_PIPELINE = Path("src/finam_core/pipelines/paper_pipeline.py")
SYMBOL_STRATEGY_MAP = Path("src/finam_core/strategy/symbol_strategy_map.py")


def read_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return path.read_text(errors="ignore").splitlines()


def context(lines: list[str], lineno: int, before: int = 10, after: int = 30) -> list[tuple[int, str]]:
    start = max(1, lineno - before)
    end = min(len(lines), lineno + after)
    return [(i, lines[i - 1]) for i in range(start, end + 1)]


def find_def(lines: list[str], name: str) -> int:
    for idx, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith(f"def {name}("):
            return idx
    return 0


def collect_function(lines: list[str], def_lineno: int) -> list[tuple[int, str]]:
    if def_lineno <= 0:
        return []

    rows: list[tuple[int, str]] = []
    base_indent = len(lines[def_lineno - 1]) - len(lines[def_lineno - 1].lstrip())

    for idx in range(def_lineno, len(lines) + 1):
        line = lines[idx - 1]
        stripped = line.strip()

        if idx > def_lineno and stripped.startswith("def "):
            indent = len(line) - len(line.lstrip())
            if indent <= base_indent:
                break

        if idx > def_lineno and stripped.startswith("async def "):
            indent = len(line) - len(line.lstrip())
            if indent <= base_indent:
                break

        rows.append((idx, line))

    return rows


def main() -> int:
    paper_lines = read_lines(PAPER_PIPELINE)
    symbol_map_text = SYMBOL_STRATEGY_MAP.read_text(errors="ignore") if SYMBOL_STRATEGY_MAP.exists() else ""

    print("=== EQUITY STRATEGY NAME RESOLVER AUDIT V1 ===")
    print("mode=read_only")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print("db_update=0")
    print("file_update=0")
    print(f"paper_pipeline_exists={1 if PAPER_PIPELINE.exists() else 0}")
    print(f"symbol_strategy_map_exists={1 if SYMBOL_STRATEGY_MAP.exists() else 0}")
    print()

    resolver_lineno = find_def(paper_lines, "_strategy_name_for_symbol")
    resolver_rows = collect_function(paper_lines, resolver_lineno)

    print("EQUITY_STRATEGY_NAME_RESOLVER_FUNCTION")
    print(f"resolver_lineno={resolver_lineno}")
    for no, line in resolver_rows:
        print(f"EQUITY_STRATEGY_NAME_RESOLVER_LINE lineno={no} line=\"{line.rstrip()}\"")

    print()
    print("EQUITY_STRATEGY_NAME_CALLS")
    for idx, line in enumerate(paper_lines, 1):
        if "_strategy_name_for_symbol(" in line:
            print(f"EQUITY_STRATEGY_NAME_CALL lineno={idx} line=\"{line.strip()}\"")
            print("EQUITY_STRATEGY_NAME_CALL_CONTEXT_BEGIN")
            for no, ctx in context(paper_lines, idx, before=6, after=8):
                print(f"{no}: {ctx}")
            print("EQUITY_STRATEGY_NAME_CALL_CONTEXT_END")

    print()
    print("EQUITY_SYMBOL_STRATEGY_MAP_LINES")
    for idx, line in enumerate(symbol_map_text.splitlines(), 1):
        if (
            "DEFAULT_STRATEGY" in line
            or "SBER@MISX" in line
            or "SBERP@MISX" in line
            or "VOLATILITY_BREAKOUT_EQUITY" in line
            or "MEAN_REVERSION_EQUITY" in line
            or "TREND_PULLBACK_EQUITY" in line
        ):
            print(f"EQUITY_SYMBOL_STRATEGY_MAP_LINE lineno={idx} line=\"{line.strip()}\"")

    resolver_text = "\n".join(line for _, line in resolver_rows)

    resolver_exists = resolver_lineno > 0
    resolver_uses_symbol_map = "SYMBOL_STRATEGY_MAP" in resolver_text or "DEFAULT_STRATEGY" in resolver_text
    resolver_uses_runtime_active_universe = "runtime_active_universe" in resolver_text
    resolver_uses_pg_logger = "pg_logger" in resolver_text or "_pg_logger" in resolver_text
    call_at_runtime_add = any(
        "_strategy_name_for_symbol(dynamic_symbol)" in line
        for line in paper_lines
    )

    symbol_map_has_sber_volatility = '"SBER@MISX": "VOLATILITY_BREAKOUT_EQUITY"' in symbol_map_text
    symbol_map_has_sber_trend = '"SBER@MISX": "TREND_PULLBACK_EQUITY"' in symbol_map_text
    symbol_map_has_sber_mean = '"SBER@MISX": "MEAN_REVERSION_EQUITY"' in symbol_map_text
    symbol_map_default_mean = 'DEFAULT_STRATEGY = "MEAN_REVERSION_EQUITY"' in symbol_map_text
    symbol_map_has_any_volatility = "VOLATILITY_BREAKOUT_EQUITY" in symbol_map_text

    mismatch_source_confirmed = (
        resolver_exists
        and call_at_runtime_add
        and not resolver_uses_runtime_active_universe
        and (resolver_uses_symbol_map or symbol_map_default_mean)
    )

    print()
    print("EQUITY_STRATEGY_NAME_RESOLVER_AUDIT_SUMMARY")
    print(f"resolver_exists={1 if resolver_exists else 0}")
    print(f"resolver_uses_symbol_map={1 if resolver_uses_symbol_map else 0}")
    print(f"resolver_uses_runtime_active_universe={1 if resolver_uses_runtime_active_universe else 0}")
    print(f"resolver_uses_pg_logger={1 if resolver_uses_pg_logger else 0}")
    print(f"call_at_runtime_add={1 if call_at_runtime_add else 0}")
    print(f"symbol_map_has_sber_volatility={1 if symbol_map_has_sber_volatility else 0}")
    print(f"symbol_map_has_sber_trend={1 if symbol_map_has_sber_trend else 0}")
    print(f"symbol_map_has_sber_mean={1 if symbol_map_has_sber_mean else 0}")
    print(f"symbol_map_default_mean={1 if symbol_map_default_mean else 0}")
    print(f"symbol_map_has_any_volatility={1 if symbol_map_has_any_volatility else 0}")
    print(f"mismatch_source_confirmed={1 if mismatch_source_confirmed else 0}")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print("db_update=0")
    print("file_update=0")

    if mismatch_source_confirmed:
        print("VERDICT=EQUITY_STRATEGY_NAME_RESOLVER_LEGACY_MAPPING_CONFIRMED")
    elif resolver_uses_runtime_active_universe:
        print("VERDICT=EQUITY_STRATEGY_NAME_RESOLVER_RUNTIME_AWARE")
    else:
        print("VERDICT=EQUITY_STRATEGY_NAME_RESOLVER_NEEDS_MANUAL_REVIEW")

    print("EQUITY_STRATEGY_NAME_RESOLVER_AUDIT_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
