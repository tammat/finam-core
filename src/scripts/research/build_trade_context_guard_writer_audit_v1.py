#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


# Русский комментарий:
# TRADE_CONTEXT_GUARD_WRITER_AUDIT_V1 — read-only аудит мест записи trades.
# Не меняет файлы, БД, runtime, execution и real trading.


TARGETS = [
    "src/finam_core/storage/postgres_logger.py",
    "src/finam_core/storage/postgres.py",
    "src/finam_core/pipelines/paper_pipeline.py",
]


PATTERNS = [
    "def log_fill",
    "def log_trade",
    "INSERT INTO trades",
    "insert into trades",
    "self.pg_logger.log_trade",
    "pg_logger.log_trade",
    "TradeContextGuardV1",
    "strategy",
    "timeframe",
    "continuous_symbol",
]


def print_context(path: Path, line_no: int, radius: int = 12) -> None:
    lines = path.read_text().splitlines()
    start = max(1, line_no - radius)
    end = min(len(lines), line_no + radius)
    print(f"CONTEXT_BEGIN file={path} line={line_no}")
    for idx in range(start, end + 1):
        print(f"{idx:05d}: {lines[idx - 1]}")
    print(f"CONTEXT_END file={path} line={line_no}")


def main() -> int:
    print("=== TRADE CONTEXT GUARD WRITER AUDIT V1 ===")
    print("mode=read_only")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print("db_update=0")
    print()

    total_hits = 0
    insert_hits = 0
    guard_hits = 0
    log_trade_hits = 0
    log_fill_hits = 0

    for target in TARGETS:
        path = Path(target)
        if not path.exists():
            print(f"TARGET_MISSING file={target}")
            continue

        text = path.read_text()
        lines = text.splitlines()

        print(f"TARGET file={target} lines={len(lines)}")

        for idx, line in enumerate(lines, start=1):
            lower = line.lower()
            matched = []

            for pattern in PATTERNS:
                if pattern.lower() in lower:
                    matched.append(pattern)

            if not matched:
                continue

            total_hits += 1

            if "insert into trades" in lower:
                insert_hits += 1
            if "tradecontextguardv1" in lower:
                guard_hits += 1
            if "log_trade" in lower:
                log_trade_hits += 1
            if "log_fill" in lower:
                log_fill_hits += 1

            print(
                "AUDIT_HIT "
                f"file={target} "
                f"line={idx} "
                f"patterns={','.join(matched)} "
                f"text={line.strip()}"
            )

        print()

    print("TRADE_CONTEXT_GUARD_WRITER_AUDIT_CONTEXT")
    for target in TARGETS:
        path = Path(target)
        if not path.exists():
            continue

        lines = path.read_text().splitlines()
        for idx, line in enumerate(lines, start=1):
            lower = line.lower()
            if "insert into trades" in lower or "def log_trade" in lower or "def log_fill" in lower:
                print_context(path, idx)

    print()
    print("TRADE_CONTEXT_GUARD_WRITER_AUDIT_SUMMARY")
    print(f"total_hits={total_hits}")
    print(f"insert_hits={insert_hits}")
    print(f"log_trade_hits={log_trade_hits}")
    print(f"log_fill_hits={log_fill_hits}")
    print(f"guard_hits={guard_hits}")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print("db_update=0")

    if insert_hits > 0 and guard_hits == 0:
        print("VERDICT=TRADE_CONTEXT_GUARD_WRITER_PATCH_REQUIRED")
    elif insert_hits > 0 and guard_hits > 0:
        print("VERDICT=TRADE_CONTEXT_GUARD_WRITER_PARTIALLY_PATCHED_REVIEW_REQUIRED")
    else:
        print("VERDICT=TRADE_CONTEXT_GUARD_WRITER_AUDIT_REVIEW_REQUIRED")

    print("TRADE_CONTEXT_GUARD_WRITER_AUDIT_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
