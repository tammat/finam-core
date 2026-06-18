#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


# Русский комментарий:
# TRADE_CONTEXT_GUARD_ALT_WRITER_PATCH_PLAN_V1
# Read-only план патча: найти log_trade(trade) callsites, где объект trade может идти
# без явных strategy/timeframe/continuous_symbol, несмотря на наличие этих полей в payload.


TARGET = Path("src/finam_core/pipelines/paper_pipeline.py")


def print_context(lines: list[str], line_no: int, radius: int = 24) -> None:
    start = max(1, line_no - radius)
    end = min(len(lines), line_no + radius)

    print(f"PATCH_PLAN_CONTEXT_BEGIN line={line_no}")
    for idx in range(start, end + 1):
        print(f"{idx:05d}: {lines[idx - 1]}")
    print(f"PATCH_PLAN_CONTEXT_END line={line_no}")


def main() -> int:
    print("=== TRADE CONTEXT GUARD ALT WRITER PATCH PLAN V1 ===")
    print("mode=read_only")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print("db_update=0")
    print()

    if not TARGET.exists():
        raise SystemExit(f"Missing target: {TARGET}")

    lines = TARGET.read_text().splitlines()

    log_trade_trade_calls: list[int] = []
    keyword_log_trade_calls: list[int] = []
    context_helper_hits: list[int] = []

    for idx, line in enumerate(lines, start=1):
        text = line.strip()

        if "log_trade(trade)" in text:
            log_trade_trade_calls.append(idx)

        if "log_trade(" in text and "trade)" not in text:
            keyword_log_trade_calls.append(idx)

        if any(
            token in text
            for token in (
                "trade_context_snapshot",
                "continuous_symbol",
                "strategy=",
                "timeframe=",
                "_build_trade_context",
                "TradeContextGuardV1",
            )
        ):
            context_helper_hits.append(idx)

    print("PATCH_PLAN_LOG_TRADE_CALLS")
    for line_no in log_trade_trade_calls:
        print(f"PATCH_PLAN_LOG_TRADE_OBJECT_CALL line={line_no}")

    for line_no in keyword_log_trade_calls:
        print(f"PATCH_PLAN_LOG_TRADE_KEYWORD_CALL line={line_no}")

    print()
    print("PATCH_PLAN_CONTEXT_RELEVANT_HITS")
    for line_no in context_helper_hits[-80:]:
        print(f"PATCH_PLAN_CONTEXT_HIT line={line_no} text={lines[line_no - 1].strip()}")

    print()
    print("PATCH_PLAN_CONTEXTS")
    for line_no in log_trade_trade_calls:
        print_context(lines, line_no)

    needs_patch = 1 if log_trade_trade_calls else 0

    print()
    print("TRADE_CONTEXT_GUARD_ALT_WRITER_PATCH_PLAN_SUMMARY")
    print(f"log_trade_object_calls={len(log_trade_trade_calls)}")
    print(f"log_trade_keyword_calls={len(keyword_log_trade_calls)}")
    print(f"context_helper_hits={len(context_helper_hits)}")
    print(f"needs_patch={needs_patch}")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print("db_update=0")

    if needs_patch:
        print("VERDICT=TRADE_CONTEXT_GUARD_ALT_WRITER_PATCH_REQUIRED")
    else:
        print("VERDICT=TRADE_CONTEXT_GUARD_ALT_WRITER_NO_OBJECT_CALLS_FOUND")

    print("TRADE_CONTEXT_GUARD_ALT_WRITER_PATCH_PLAN_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
