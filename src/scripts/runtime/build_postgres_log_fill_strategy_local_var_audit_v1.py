#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


# Русский комментарий:
# POSTGRES_LOG_FILL_STRATEGY_LOCAL_VAR_AUDIT_V1
# Read-only аудит мест, где fill logging может использовать strategy до присвоения.


TARGET_FILE = Path("src/finam_core/pipelines/paper_pipeline.py")

PATTERNS = [
    "POSTGRES LOG FILL FAILED",
    "log_fill",
    "fill_logged",
    "fill_id",
    "payload.setdefault(\"strategy\"",
    "strategy =",
    "strategy=",
    "_strategy_name_for_symbol",
    "NG_CONSERVATIVE_BREAKOUT_M1",
    "trade_context_snapshot",
]


def main() -> int:
    print("=== POSTGRES LOG FILL STRATEGY LOCAL VAR AUDIT V1 ===")
    print("mode=read_only")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print("db_update=0")
    print(f"target_file={TARGET_FILE}")

    text = TARGET_FILE.read_text(encoding="utf-8", errors="ignore")
    lines = text.splitlines()

    hits: list[tuple[int, str, str]] = []
    for i, line in enumerate(lines, start=1):
        for pattern in PATTERNS:
            if pattern in line:
                hits.append((i, pattern, line.strip()))

    print()
    print("POSTGRES_LOG_FILL_STRATEGY_AUDIT_HITS")
    for line_no, pattern, line in hits:
        print(
            "POSTGRES_LOG_FILL_STRATEGY_AUDIT_HIT "
            f"line={line_no} "
            f"pattern={pattern} "
            f"text={line[:240]}"
        )

    print()
    print("POSTGRES_LOG_FILL_STRATEGY_AUDIT_CONTEXT")
    for line_no, pattern, _ in hits:
        if pattern in {"POSTGRES LOG FILL FAILED", "log_fill", "fill_logged"}:
            start = max(1, line_no - 25)
            end = min(len(lines), line_no + 30)
            print(f"POSTGRES_LOG_FILL_STRATEGY_AUDIT_CONTEXT_BEGIN pattern={pattern} line={line_no}")
            for no in range(start, end + 1):
                print(f"{no}: {lines[no - 1]}")
            print(f"POSTGRES_LOG_FILL_STRATEGY_AUDIT_CONTEXT_END pattern={pattern} line={line_no}")

    has_error_log = int("POSTGRES LOG FILL FAILED" in text)
    has_strategy_setdefault = int('payload.setdefault("strategy"' in text)
    has_trade_context_snapshot = int("trade_context_snapshot" in text)

    print()
    print("POSTGRES_LOG_FILL_STRATEGY_AUDIT_SUMMARY")
    print(f"hits={len(hits)}")
    print(f"has_error_log={has_error_log}")
    print(f"has_strategy_setdefault={has_strategy_setdefault}")
    print(f"has_trade_context_snapshot={has_trade_context_snapshot}")
    print("db_update=0")
    print("execution_changes_required=0")
    print("runtime_changes_required=0")

    if has_error_log:
        print("VERDICT=POSTGRES_LOG_FILL_STRATEGY_LOCAL_VAR_REVIEW_REQUIRED")
    else:
        print("VERDICT=POSTGRES_LOG_FILL_ERROR_LOG_NOT_FOUND")

    print("POSTGRES_LOG_FILL_STRATEGY_LOCAL_VAR_AUDIT_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
