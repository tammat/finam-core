#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


# Русский комментарий:
# EQUITY_PRE_SIGNAL_GUARD_CALLSITE_AUDIT_V1 — read-only аудит всех мест,
# где пишется runtime_guard_pre_signal_block_audit_v1 через _save_pre_signal_block_audit_v1.
# Ничего не меняет в коде, БД, runtime, systemd и execution.
# Цель — найти оставшийся callsite, который пишет SBER@MISX strategy=MEAN_REVERSION_EQUITY.


PAPER_PIPELINE = Path("src/finam_core/pipelines/paper_pipeline.py")


def read_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return path.read_text(errors="ignore").splitlines()


def context(lines: list[str], lineno: int, before: int = 12, after: int = 24) -> list[tuple[int, str]]:
    start = max(1, lineno - before)
    end = min(len(lines), lineno + after)
    return [(i, lines[i - 1]) for i in range(start, end + 1)]


def collect_call_block(lines: list[str], lineno: int) -> list[tuple[int, str]]:
    rows: list[tuple[int, str]] = []
    balance = 0
    started = False

    for idx in range(max(1, lineno - 6), min(len(lines), lineno + 40) + 1):
        line = lines[idx - 1]
        rows.append((idx, line))

        if "_save_pre_signal_block_audit_v1(" in line:
            started = True

        if started:
            balance += line.count("(")
            balance -= line.count(")")

        if started and balance <= 0 and idx > lineno:
            break

    return rows


def main() -> int:
    lines = read_lines(PAPER_PIPELINE)

    print("=== EQUITY PRE SIGNAL GUARD CALLSITE AUDIT V1 ===")
    print("mode=read_only")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print("db_update=0")
    print("file_update=0")
    print(f"paper_pipeline_exists={1 if PAPER_PIPELINE.exists() else 0}")
    print(f"paper_pipeline_lines={len(lines)}")
    print()

    callsites: list[int] = []
    save_method_defs: list[int] = []

    for idx, line in enumerate(lines, 1):
        if "_save_pre_signal_block_audit_v1(" in line:
            if line.strip().startswith("def "):
                save_method_defs.append(idx)
            else:
                callsites.append(idx)

    patched_calls = 0
    legacy_calls = 0
    unclear_calls = 0

    print("EQUITY_PRE_SIGNAL_GUARD_CALLSITES")
    for call_lineno in callsites:
        block_rows = collect_call_block(lines, call_lineno)
        block_text = "\n".join(line for _, line in block_rows)

        has_runtime_resolver = "_runtime_strategy_name_for_symbol" in block_text
        has_legacy_resolver = "_strategy_name_for_symbol" in block_text
        has_vol_low = 'block_type="VOL_LOW_BLOCK"' in block_text or "VOL_LOW_BLOCK" in block_text
        has_compression = 'block_type="COMPRESSION_WATCH"' in block_text or "COMPRESSION_WATCH" in block_text
        has_runtime_patch_marker = "EQUITY_PRE_SIGNAL_GUARD_STRATEGY_WIRING_PATCH_V1" in block_text

        if has_runtime_resolver:
            patched_calls += 1
            status = "PATCHED_RUNTIME_RESOLVER"
        elif has_legacy_resolver:
            legacy_calls += 1
            status = "LEGACY_RESOLVER"
        else:
            unclear_calls += 1
            status = "UNCLEAR_STRATEGY_SOURCE"

        print(
            "EQUITY_PRE_SIGNAL_GUARD_CALLSITE "
            f"lineno={call_lineno} "
            f"status={status} "
            f"has_runtime_resolver={1 if has_runtime_resolver else 0} "
            f"has_legacy_resolver={1 if has_legacy_resolver else 0} "
            f"has_vol_low={1 if has_vol_low else 0} "
            f"has_compression={1 if has_compression else 0} "
            f"has_patch_marker={1 if has_runtime_patch_marker else 0}"
        )

        print("EQUITY_PRE_SIGNAL_GUARD_CALLSITE_CONTEXT_BEGIN")
        for no, ctx_line in block_rows:
            print(f"{no}: {ctx_line}")
        print("EQUITY_PRE_SIGNAL_GUARD_CALLSITE_CONTEXT_END")

    print()
    print("EQUITY_PRE_SIGNAL_GUARD_SAVE_METHOD_DEFS")
    for lineno in save_method_defs:
        print(f"EQUITY_PRE_SIGNAL_GUARD_SAVE_METHOD_DEF lineno={lineno} line=\"{lines[lineno - 1].strip()}\"")
        print("EQUITY_PRE_SIGNAL_GUARD_SAVE_METHOD_CONTEXT_BEGIN")
        for no, ctx in context(lines, lineno, before=4, after=45):
            print(f"{no}: {ctx}")
        print("EQUITY_PRE_SIGNAL_GUARD_SAVE_METHOD_CONTEXT_END")

    unresolved_legacy = legacy_calls + unclear_calls

    print()
    print("EQUITY_PRE_SIGNAL_GUARD_CALLSITE_AUDIT_SUMMARY")
    print(f"callsites_total={len(callsites)}")
    print(f"patched_calls={patched_calls}")
    print(f"legacy_calls={legacy_calls}")
    print(f"unclear_calls={unclear_calls}")
    print(f"unresolved_legacy={unresolved_legacy}")
    print(f"save_method_defs={len(save_method_defs)}")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print("db_update=0")
    print("file_update=0")

    if len(callsites) > 0 and unresolved_legacy == 0:
        print("VERDICT=EQUITY_PRE_SIGNAL_GUARD_CALLSITES_PATCHED")
    elif unresolved_legacy > 0:
        print("VERDICT=EQUITY_PRE_SIGNAL_GUARD_LEGACY_CALLSITES_FOUND")
    else:
        print("VERDICT=EQUITY_PRE_SIGNAL_GUARD_CALLSITES_NEED_REVIEW")

    print("EQUITY_PRE_SIGNAL_GUARD_CALLSITE_AUDIT_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
