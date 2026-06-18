#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]

TARGETS = [
    "src/finam_core/storage/postgres.py",
    "src/finam_core/storage/postgres_logger.py",
    "src/finam_core/execution/fill_persistence_service.py",
]

PATTERNS = [
    "def ",
    "class ",
    "insert into trades",
    "INSERT INTO trades",
    "strategy",
    "timeframe",
    "continuous_symbol",
    "payload",
    "log_fill",
    "trade_source",
    "fill_id",
    "execute(",
]


def extract_hits(text: str) -> list[tuple[int, str]]:
    hits: list[tuple[int, str]] = []

    for line_no, line in enumerate(text.splitlines(), start=1):
        lower = line.lower()
        if any(p.lower() in lower for p in PATTERNS):
            hits.append((line_no, line.rstrip()))

    return hits


def print_window(lines: list[str], center: int, radius: int = 18) -> None:
    start = max(1, center - radius)
    end = min(len(lines), center + radius)

    for line_no in range(start, end + 1):
        print(
            "STORAGE_WRITER_CONTEXT "
            f"line={line_no} "
            f"text={lines[line_no - 1].rstrip()}"
        )


def main() -> int:
    print("=== STORAGE TRADE WRITER CONTEXT AUDIT V1 ===")
    print("mode=diagnostic")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")

    writer_files = 0
    insert_sites = 0
    log_fill_sites = 0

    for rel in TARGETS:
        path = ROOT / rel
        print()
        print(f"STORAGE_WRITER_FILE path={rel} exists={int(path.exists())}")

        if not path.exists():
            continue

        writer_files += 1
        text = path.read_text(errors="ignore")
        lines = text.splitlines()
        hits = extract_hits(text)

        direct_insert_lines = []
        log_fill_lines = []

        for line_no, line in hits:
            lower = line.lower()
            if "insert into trades" in lower:
                direct_insert_lines.append(line_no)
            if "log_fill" in lower:
                log_fill_lines.append(line_no)

        insert_sites += len(direct_insert_lines)
        log_fill_sites += len(log_fill_lines)

        print(
            "STORAGE_WRITER_FILE_SUMMARY "
            f"path={rel} "
            f"hits={len(hits)} "
            f"direct_insert_sites={len(direct_insert_lines)} "
            f"log_fill_sites={len(log_fill_lines)}"
        )

        print()
        print(f"STORAGE_WRITER_HITS path={rel}")
        for line_no, line in hits[:160]:
            print(
                "STORAGE_WRITER_HIT "
                f"path={rel} "
                f"line={line_no} "
                f"text={line}"
            )

        for line_no in direct_insert_lines + log_fill_lines:
            print()
            print(
                "STORAGE_WRITER_CONTEXT_WINDOW "
                f"path={rel} "
                f"center_line={line_no}"
            )
            print_window(lines, line_no)

    print()
    print("STORAGE_TRADE_WRITER_CONTEXT_AUDIT_SUMMARY")
    print(f"writer_files={writer_files}")
    print(f"direct_insert_sites={insert_sites}")
    print(f"log_fill_sites={log_fill_sites}")

    if insert_sites == 0 and log_fill_sites == 0:
        print("VERDICT=STORAGE_TRADE_WRITER_CONTEXT_AUDIT_NO_INSERT_SITE")
        return 1

    print("VERDICT=STORAGE_TRADE_WRITER_CONTEXT_AUDIT_READY")
    print("STORAGE_TRADE_WRITER_CONTEXT_AUDIT_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
