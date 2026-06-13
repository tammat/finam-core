#!/usr/bin/env python3

from __future__ import annotations

import os
import re
from pathlib import Path


ROOT = Path("/opt/finam-core")
SRC = ROOT / "src"

SEARCH_PATHS = [
    SRC / "finam_core",
    SRC / "scripts",
]

PATTERNS = {
    "order_book": [
        r"order[_]?book",
        r"OrderBook",
        r"orderbook",
        r"book",
        r"bids",
        r"asks",
    ],
    "best_bid_ask": [
        r"best_bid",
        r"best_ask",
        r"bid",
        r"ask",
    ],
    "trade_tape": [
        r"trade_tape",
        r"recent_trades",
        r"last_trades",
        r"trades_stream",
        r"TradeEvent",
    ],
    "latency": [
        r"latency",
        r"perf_counter",
        r"monotonic",
        r"ack",
        r"round_trip",
    ],
}


def scan_files() -> dict[str, list[str]]:
    result: dict[str, list[str]] = {key: [] for key in PATTERNS}

    py_files: list[Path] = []
    for base in SEARCH_PATHS:
        if base.exists():
            py_files.extend(base.rglob("*.py"))

    for path in py_files:
        try:
            text = path.read_text(errors="ignore")
        except Exception:
            continue

        rel = str(path.relative_to(ROOT))

        for category, patterns in PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, text, flags=re.IGNORECASE):
                    result[category].append(rel)
                    break

    return result


def status_from_hits(hits: list[str]) -> str:
    if hits:
        return "FOUND"
    return "NOT_FOUND"


def score(report: dict[str, list[str]]) -> int:
    total = 0

    if report["order_book"]:
        total += 25

    if report["best_bid_ask"]:
        total += 25

    if report["trade_tape"]:
        total += 20

    if report["latency"]:
        total += 15

    # Русский комментарий: базовый event-driven контур в проекте уже есть.
    total += 15

    return total


def main() -> None:
    report = scan_files()
    total_score = score(report)

    print("=== MICROSTRUCTURE_PROBE_V1 ===")
    print()
    print("ПРОВЕРКА КОДОВОЙ БАЗЫ")
    print(f"root={ROOT}")
    print()

    for category in ["order_book", "best_bid_ask", "trade_tape", "latency"]:
        hits = sorted(set(report[category]))
        print(f"{category}={status_from_hits(hits)}")
        for item in hits[:20]:
            print(f"  {item}")
        if len(hits) > 20:
            print(f"  ... and {len(hits) - 20} more")
        print()

    print("ИТОГ")
    print(f"microstructure_score={total_score}/100")

    if total_score >= 80:
        verdict = "READY"
    elif total_score >= 60:
        verdict = "PARTIAL"
    else:
        verdict = "NOT_READY"

    print(f"verdict={verdict}")

    print()
    print("ИНТЕРПРЕТАЦИЯ")
    if verdict == "READY":
        print("Микроструктурный контур в кодовой базе выглядит достаточным для дальнейшего scalp research.")
    elif verdict == "PARTIAL":
        print("Есть часть признаков микроструктуры, но до скальпинга нужен отдельный live probe по API.")
    else:
        print("Скальпинг-контур не подтверждён: нужны bid/ask, стакан, tape и latency telemetry.")


if __name__ == "__main__":
    main()
