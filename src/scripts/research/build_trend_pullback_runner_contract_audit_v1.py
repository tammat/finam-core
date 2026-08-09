#!/usr/bin/env python3
"""
TREND_PULLBACK_RUNNER_CONTRACT_AUDIT_V1

Read-only source-contract audit.

Проверяет:
- где реально реализован TREND_PULLBACK_V1;
- поддерживает ли его build_strategy_execution_runner_v1;
- существует ли canonical trend_pullback_signal;
- есть ли parameter references fast_ma/slow_ma/pullback/hold.

Никаких backtest / DB writes / runtime changes.
"""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path("/opt/finam-core")

RUNNER = ROOT / (
    "src/scripts/"
    "build_strategy_execution_runner_v1.py"
)

ADAPTER = ROOT / (
    "src/finam_core/research/"
    "postgresql_edge_backtest_adapter_v1.py"
)

STRATEGY_CODE = "TREND_PULLBACK_V1"

PARAMETER_TOKENS = (
    "fast_ma",
    "slow_ma",
    "pullback_atr",
    "pullback_atr_multiplier",
    "hold_bars",
)


def parse_ok(path: Path) -> bool:
    try:
        ast.parse(
            path.read_text(
                encoding="utf-8",
                errors="ignore",
            )
        )
        return True
    except (OSError, SyntaxError):
        return False


def lines_with(
    text: str,
    token: str,
) -> list[int]:
    return [
        no
        for no, line in enumerate(
            text.splitlines(),
            start=1,
        )
        if token.lower() in line.lower()
    ]


def main() -> int:
    print(
        "=== TREND PULLBACK RUNNER "
        "CONTRACT AUDIT V1 ==="
    )
    print("mode=read_only_source_contract")

    runner_exists = RUNNER.is_file()
    adapter_exists = ADAPTER.is_file()

    runner_text = (
        RUNNER.read_text(
            encoding="utf-8",
            errors="ignore",
        )
        if runner_exists
        else ""
    )

    adapter_text = (
        ADAPTER.read_text(
            encoding="utf-8",
            errors="ignore",
        )
        if adapter_exists
        else ""
    )

    runner_strategy_lines = lines_with(
        runner_text,
        STRATEGY_CODE,
    )

    adapter_strategy_lines = lines_with(
        adapter_text,
        STRATEGY_CODE,
    )

    adapter_signal_lines = lines_with(
        adapter_text,
        "def trend_pullback_signal",
    )

    print(
        "SOURCE_ROW "
        "component=strategy_execution_runner "
        f"exists={int(runner_exists)} "
        f"syntax_ok={int(parse_ok(RUNNER) if runner_exists else False)} "
        f"strategy_code_hits={len(runner_strategy_lines)} "
        "lines="
        + (
            ",".join(
                str(value)
                for value in runner_strategy_lines
            )
            if runner_strategy_lines
            else "NONE"
        )
    )

    print(
        "SOURCE_ROW "
        "component=postgresql_edge_backtest_adapter "
        f"exists={int(adapter_exists)} "
        f"syntax_ok={int(parse_ok(ADAPTER) if adapter_exists else False)} "
        f"strategy_code_hits={len(adapter_strategy_lines)} "
        f"signal_function_hits={len(adapter_signal_lines)}"
    )

    runner_parameter_hits = {}

    for token in PARAMETER_TOKENS:
        hits = lines_with(
            runner_text,
            token,
        )
        runner_parameter_hits[token] = hits

        print(
            "RUNNER_PARAMETER_ROW "
            f"parameter={token} "
            f"hits={len(hits)} "
            "lines="
            + (
                ",".join(
                    str(value)
                    for value in hits[:20]
                )
                if hits
                else "NONE"
            )
        )

    adapter_parameter_hits = {}

    for token in PARAMETER_TOKENS:
        hits = lines_with(
            adapter_text,
            token,
        )
        adapter_parameter_hits[token] = hits

        print(
            "ADAPTER_PARAMETER_ROW "
            f"parameter={token} "
            f"hits={len(hits)} "
            "lines="
            + (
                ",".join(
                    str(value)
                    for value in hits[:20]
                )
                if hits
                else "NONE"
            )
        )

    runner_support_confirmed = (
        bool(runner_strategy_lines)
        and any(
            runner_parameter_hits[token]
            for token in PARAMETER_TOKENS
        )
    )

    canonical_adapter_confirmed = (
        bool(adapter_strategy_lines)
        and bool(adapter_signal_lines)
    )

    print()
    print(
        f"runner_support_confirmed="
        f"{int(runner_support_confirmed)}"
    )
    print(
        f"canonical_adapter_confirmed="
        f"{int(canonical_adapter_confirmed)}"
    )

    print("backtest_performed=0")
    print("parameter_search_performed=0")
    print("db_writes_performed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")

    if (
        canonical_adapter_confirmed
        and not runner_support_confirmed
    ):
        verdict = (
            "TREND_PULLBACK_CANONICAL_ADAPTER_"
            "CONFIRMED_RUNNER_UNSUPPORTED"
        )
    elif (
        canonical_adapter_confirmed
        and runner_support_confirmed
    ):
        verdict = (
            "TREND_PULLBACK_RUNNER_AND_"
            "ADAPTER_CONTRACT_CONFIRMED"
        )
    else:
        verdict = (
            "TREND_PULLBACK_CONTRACT_"
            "REVIEW_REQUIRED"
        )

    print(f"VERDICT={verdict}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
