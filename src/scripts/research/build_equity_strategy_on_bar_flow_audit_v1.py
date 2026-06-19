#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


# Русский комментарий:
# EQUITY_STRATEGY_ON_BAR_FLOW_AUDIT_V1
# Read-only code audit.
# Цель — найти маршрут paper_pipeline:
# fresh bar -> symbol dispatch -> strategy_by_symbol -> strategy call -> guard/signal.
# Ничего не меняет.


ROOT = Path(".").resolve()

TARGET_FILES = [
    Path("src/finam_core/pipelines/paper_pipeline.py"),
    Path("src/finam_core/strategy/equities/volatility_breakout_equity.py"),
    Path("src/finam_core/strategy/strategy_factory.py"),
]

TERMS = [
    "strategy_by_symbol",
    "on_bar",
    "generate",
    "signal",
    "signals",
    "process_bar",
    "market_bars",
    "dynamic_symbol",
    "SBER@MISX",
    "VOLATILITY_BREAKOUT_EQUITY",
    "_runtime_strategy_name_for_symbol",
    "_save_pre_signal_block_audit_v1",
    "PIPE_RUNTIME_SYMBOL_STRATEGY_CREATED",
    "PIPE_EQUITY",
    "runtime_active_universe",
    "symbol.endswith(\"@MISX\")",
    "@MISX",
]


def read_lines(path: Path) -> list[str]:
    try:
        return path.read_text(encoding="utf-8", errors="replace").splitlines()
    except FileNotFoundError:
        return []


def emit_context(path: Path, line_no: int, lines: list[str], term: str) -> None:
    start = max(1, line_no - 5)
    end = min(len(lines), line_no + 8)

    print(
        "EQUITY_ON_BAR_FLOW_CODE_HIT "
        f"file={path} "
        f"line={line_no} "
        f"term={term}"
    )

    for idx in range(start, end + 1):
        print(
            "EQUITY_ON_BAR_FLOW_CODE_CONTEXT "
            f"file={path} "
            f"line={idx} "
            f"code={lines[idx - 1].strip()}"
        )


def main() -> int:
    print("=== EQUITY STRATEGY ON BAR FLOW AUDIT V1 ===")
    print("mode=read_only")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print("db_update=0")
    print(f"root={ROOT}")
    print()

    hits: list[tuple[str, int, str]] = []

    for rel in TARGET_FILES:
        path = ROOT / rel
        lines = read_lines(path)

        if not lines:
            print(f"EQUITY_ON_BAR_FLOW_FILE_MISSING file={rel}")
            continue

        for line_no, line in enumerate(lines, start=1):
            for term in TERMS:
                if term in line:
                    hits.append((str(rel), line_no, term))
                    emit_context(rel, line_no, lines, term)

    files_with_hits = len({h[0] for h in hits})
    strategy_by_symbol_hits = len([h for h in hits if h[2] == "strategy_by_symbol"])
    on_bar_hits = len([h for h in hits if h[2] == "on_bar"])
    equity_route_hits = len([h for h in hits if h[2] in {"@MISX", "symbol.endswith(\"@MISX\")", "VOLATILITY_BREAKOUT_EQUITY"}])
    guard_hits = len([h for h in hits if h[2] == "_save_pre_signal_block_audit_v1"])
    runtime_strategy_hits = len([h for h in hits if h[2] == "_runtime_strategy_name_for_symbol"])

    print()
    print("EQUITY_STRATEGY_ON_BAR_FLOW_AUDIT_SUMMARY")
    print(f"files_with_hits={files_with_hits}")
    print(f"hits_total={len(hits)}")
    print(f"strategy_by_symbol_hits={strategy_by_symbol_hits}")
    print(f"on_bar_hits={on_bar_hits}")
    print(f"equity_route_hits={equity_route_hits}")
    print(f"guard_hits={guard_hits}")
    print(f"runtime_strategy_hits={runtime_strategy_hits}")
    print("db_update=0")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print("real_trading_enabled=0")
    print("execution_enabled=0")

    if strategy_by_symbol_hits > 0 and on_bar_hits > 0:
        print("VERDICT=EQUITY_ON_BAR_FLOW_CALLSITES_FOUND")
    elif strategy_by_symbol_hits > 0:
        print("VERDICT=EQUITY_STRATEGY_REGISTRY_FOUND_ON_BAR_REVIEW_REQUIRED")
    else:
        print("VERDICT=EQUITY_ON_BAR_FLOW_CALLSITES_NOT_FOUND")

    print("EQUITY_STRATEGY_ON_BAR_FLOW_AUDIT_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
