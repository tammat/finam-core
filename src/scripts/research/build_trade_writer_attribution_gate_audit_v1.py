#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]

SEARCH_DIRS = [
    "src/finam_core",
    "src/scripts",
]

PATTERNS = [
    "insert into trades",
    "INSERT INTO trades",
    "trades (",
    "table_name='trades'",
    'table_name="trades"',
    ".insert(",
    "log_fill",
    "log_trade",
    "save_trade",
    "record_trade",
    "persist_trade",
    "trade_source",
]

IGNORE_PARTS = [
    "__pycache__",
    ".pyc",
    ".bak",
    ".bak_",
    "build_trade_context_backfill_from_payload_v1.py",
    "apply_trade_context_backfill_from_payload_v1.py",
    "build_closed_trade_edge_scorecard",
    "build_trade_context_snapshot_completeness",
    "build_runtime_strategy_quarantine",
    "build_edge_runtime_action",
    "build_trade_writer_attribution_gate_audit_v1.py",
]

LIKELY_WRITER_MARKERS = [
    "insert into trades",
    "INSERT INTO trades",
    "log_fill",
    "log_trade",
    "save_trade",
    "record_trade",
    "persist_trade",
]

CONTEXT_MARKERS = [
    "strategy",
    "timeframe",
    "continuous_symbol",
    "payload",
    "trade_source",
    "fill_id",
]


def should_skip(path: Path) -> bool:
    text = str(path)
    return any(part in text for part in IGNORE_PARTS)


def classify_file(rel: str, content: str) -> tuple[str, str]:
    lower = content.lower()

    has_insert = "insert into trades" in lower
    has_log_fill = "log_fill" in lower
    has_trade_source = "trade_source" in lower
    has_strategy = "strategy" in lower
    has_timeframe = "timeframe" in lower
    has_cont = "continuous_symbol" in lower

    if has_insert and has_strategy and has_timeframe:
        return "PRIMARY_TRADE_WRITER_CANDIDATE", "direct insert into trades with context fields"

    if has_insert:
        return "TRADE_INSERT_REQUIRES_GATE_REVIEW", "direct insert into trades found"

    if has_log_fill and has_trade_source:
        return "FILL_LOGGER_CANDIDATE", "log_fill and trade_source found"

    if has_log_fill:
        return "FILL_LOGGER_REVIEW", "log_fill found"

    if "trades" in lower and has_trade_source:
        return "TRADE_REPOSITORY_REVIEW", "trades and trade_source found"

    return "CONTEXT_ONLY", "no direct writer marker"


def extract_hits(content: str) -> list[tuple[int, str]]:
    hits: list[tuple[int, str]] = []

    for line_no, line in enumerate(content.splitlines(), start=1):
        lower = line.lower()
        if any(pattern.lower() in lower for pattern in PATTERNS):
            hits.append((line_no, line.rstrip()))

    return hits


def main() -> int:
    print("=== TRADE WRITER ATTRIBUTION GATE AUDIT V1 ===")
    print("mode=diagnostic")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")

    rows = []

    for base in SEARCH_DIRS:
        base_path = ROOT / base
        if not base_path.exists():
            continue

        for path in sorted(base_path.rglob("*.py")):
            if should_skip(path):
                continue

            content = path.read_text(errors="ignore")
            hits = extract_hits(content)

            if not hits:
                continue

            rel = str(path.relative_to(ROOT))
            classification, reason = classify_file(rel, content)

            rows.append((rel, classification, reason, hits))

    primary = [row for row in rows if row[1] == "PRIMARY_TRADE_WRITER_CANDIDATE"]
    insert_review = [row for row in rows if row[1] == "TRADE_INSERT_REQUIRES_GATE_REVIEW"]
    fill_logger = [row for row in rows if row[1] in {"FILL_LOGGER_CANDIDATE", "FILL_LOGGER_REVIEW"}]

    print()
    print("TRADE_WRITER_AUDIT_ROWS")

    for rel, classification, reason, hits in rows:
        print(
            "TRADE_WRITER_ROW "
            f"path={rel} "
            f"classification={classification} "
            f"hits={len(hits)} "
            f"reason={reason}"
        )

        for line_no, line in hits[:80]:
            print(
                "TRADE_WRITER_HIT "
                f"path={rel} "
                f"line={line_no} "
                f"text={line}"
            )

    print()
    print("TRADE_WRITER_AUDIT_SUMMARY")
    print(f"rows={len(rows)}")
    print(f"primary_trade_writer_candidates={len(primary)}")
    print(f"trade_insert_review={len(insert_review)}")
    print(f"fill_logger_candidates={len(fill_logger)}")

    if primary:
        print("PRIMARY_CANDIDATES=" + ",".join(row[0] for row in primary))
    else:
        print("PRIMARY_CANDIDATES=none")

    if insert_review:
        print("INSERT_REVIEW=" + ",".join(row[0] for row in insert_review))
    else:
        print("INSERT_REVIEW=none")

    if fill_logger:
        print("FILL_LOGGER_CANDIDATES=" + ",".join(row[0] for row in fill_logger))
    else:
        print("FILL_LOGGER_CANDIDATES=none")

    if not primary and not insert_review and not fill_logger:
        print("VERDICT=TRADE_WRITER_ATTRIBUTION_GATE_AUDIT_NO_WRITER_FOUND")
        return 1

    print("VERDICT=TRADE_WRITER_ATTRIBUTION_GATE_AUDIT_READY")
    print("TRADE_WRITER_ATTRIBUTION_GATE_AUDIT_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
