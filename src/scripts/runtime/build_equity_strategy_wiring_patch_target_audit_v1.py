#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


# Русский комментарий:
# EQUITY_STRATEGY_WIRING_PATCH_TARGET_AUDIT_V1 — read-only аудит точек патча.
# Скрипт не меняет paper_pipeline.py, БД, runtime, systemd и execution.
# Цель — найти конкретный StrategyFactory.create(...) блок и подтвердить,
# что будущий патч можно ограничить equity strategy resolution path.


PAPER_PIPELINE = Path("src/finam_core/pipelines/paper_pipeline.py")


def read_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return path.read_text(errors="ignore").splitlines()


def context(lines: list[str], lineno: int, before: int = 8, after: int = 12) -> list[tuple[int, str]]:
    start = max(1, lineno - before)
    end = min(len(lines), lineno + after)
    return [(i, lines[i - 1]) for i in range(start, end + 1)]


def collect_block(lines: list[str], lineno: int) -> str:
    # Русский комментарий:
    # Собираем небольшой блок от строки StrategyFactory.create до закрытия вызова.
    collected: list[str] = []
    balance = 0
    started = False

    for i in range(lineno, min(len(lines), lineno + 20) + 1):
        line = lines[i - 1]
        collected.append(line)

        if "StrategyFactory.create" in line:
            started = True

        if started:
            balance += line.count("(")
            balance -= line.count(")")

        if started and balance <= 0 and i > lineno:
            break

    return "\n".join(collected)


def main() -> int:
    lines = read_lines(PAPER_PIPELINE)

    print("=== EQUITY STRATEGY WIRING PATCH TARGET AUDIT V1 ===")
    print("mode=read_only")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print("db_update=0")
    print("file_update=0")
    print(f"paper_pipeline_exists={1 if PAPER_PIPELINE.exists() else 0}")
    print(f"paper_pipeline_lines={len(lines)}")
    print()

    if not lines:
        print("EQUITY_PATCH_TARGET_AUDIT_SUMMARY")
        print("strategy_factory_create_blocks=0")
        print("equity_candidate_blocks=0")
        print("patch_target_found=0")
        print("VERDICT=EQUITY_PATCH_TARGET_AUDIT_NO_FILE")
        print("EQUITY_STRATEGY_WIRING_PATCH_TARGET_AUDIT_V1_OK")
        return 0

    create_lines: list[int] = []
    mean_reversion_lines: list[int] = []
    runtime_universe_lines: list[int] = []
    misx_lines: list[int] = []

    for idx, line in enumerate(lines, 1):
        if "StrategyFactory.create" in line:
            create_lines.append(idx)
        if "self.mean_reversion" in line or "MeanReversionStrategy" in line:
            mean_reversion_lines.append(idx)
        if "runtime_active_universe" in line or "_runtime_active_universe_allows_paper" in line:
            runtime_universe_lines.append(idx)
        if "@MISX" in line or "MISX" in line:
            misx_lines.append(idx)

    print("EQUITY_PATCH_TARGET_FACTORY_CREATE_BLOCKS")
    equity_candidate_blocks = 0
    patch_target_found = 0

    for lineno in create_lines:
        block = collect_block(lines, lineno)
        nearby = "\n".join(line for _, line in context(lines, lineno, before=30, after=30))

        has_symbol_strategy_keyword = "symbol=" in block and "strategy_name=" in block
        has_positional_only = (
            "StrategyFactory.create(" in block
            and "strategy_name=" not in block
            and "symbol=" not in block
        )
        near_runtime = "runtime_active_universe" in nearby or "active_strategy" in nearby or "runtime_strategy" in nearby
        near_dynamic_symbol = "dynamic_symbol" in nearby
        near_misx = "@MISX" in nearby or "MISX" in nearby
        near_ng = "NG" in nearby or "_ng_strategy_for_symbol" in nearby
        near_br = "BR" in nearby or "br_symbol" in nearby

        is_equity_candidate = near_dynamic_symbol or near_misx or near_runtime
        if is_equity_candidate:
            equity_candidate_blocks += 1

        if is_equity_candidate and has_positional_only:
            patch_target_found += 1

        print(
            "EQUITY_PATCH_TARGET_FACTORY_CREATE_BLOCK "
            f"lineno={lineno} "
            f"has_symbol_strategy_keyword={1 if has_symbol_strategy_keyword else 0} "
            f"has_positional_only={1 if has_positional_only else 0} "
            f"near_runtime={1 if near_runtime else 0} "
            f"near_dynamic_symbol={1 if near_dynamic_symbol else 0} "
            f"near_misx={1 if near_misx else 0} "
            f"near_ng={1 if near_ng else 0} "
            f"near_br={1 if near_br else 0} "
            f"is_equity_candidate={1 if is_equity_candidate else 0}"
        )

        print("EQUITY_PATCH_TARGET_FACTORY_CREATE_CONTEXT_BEGIN")
        for no, ctx_line in context(lines, lineno, before=8, after=12):
            print(f"{no}: {ctx_line}")
        print("EQUITY_PATCH_TARGET_FACTORY_CREATE_CONTEXT_END")

    print()
    print("EQUITY_PATCH_TARGET_LEGACY_MEAN_REVERSION_LINES")
    for lineno in mean_reversion_lines:
        print(f"EQUITY_PATCH_TARGET_LEGACY_MEAN_REVERSION_LINE lineno={lineno} line=\"{lines[lineno - 1].strip()}\"")

    print()
    print("EQUITY_PATCH_TARGET_RUNTIME_UNIVERSE_LINES")
    for lineno in runtime_universe_lines[:40]:
        print(f"EQUITY_PATCH_TARGET_RUNTIME_UNIVERSE_LINE lineno={lineno} line=\"{lines[lineno - 1].strip()}\"")

    print()
    print("EQUITY_PATCH_TARGET_AUDIT_SUMMARY")
    print(f"strategy_factory_create_blocks={len(create_lines)}")
    print(f"equity_candidate_blocks={equity_candidate_blocks}")
    print(f"patch_target_found={patch_target_found}")
    print(f"legacy_mean_reversion_lines={len(mean_reversion_lines)}")
    print(f"runtime_universe_lines={len(runtime_universe_lines)}")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print("db_update=0")
    print("file_update=0")

    if patch_target_found > 0:
        print("VERDICT=EQUITY_PATCH_TARGET_FOUND")
    elif equity_candidate_blocks > 0:
        print("VERDICT=EQUITY_PATCH_TARGET_REVIEW_REQUIRED")
    else:
        print("VERDICT=EQUITY_PATCH_TARGET_NOT_FOUND")

    print("EQUITY_STRATEGY_WIRING_PATCH_TARGET_AUDIT_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
