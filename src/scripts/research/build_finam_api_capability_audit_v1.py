#!/usr/bin/env python3

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path("/opt/finam-core")
SRC = ROOT / "src"

CAPABILITIES = {
    "CANDLES_OR_BARS": [r"candles?", r"bars?", r"Get.*Candles", r"market_bars"],
    "QUOTES_LAST": [r"quote", r"last_price", r"last"],
    "ORDER_BOOK": [r"order[_]?book", r"OrderBook", r"bids", r"asks", r"Get.*OrderBook"],
    "BEST_BID_ASK": [r"best_bid", r"best_ask", r"\bbid\b", r"\bask\b"],
    "TRADE_TAPE": [r"trade_tape", r"recent_trades", r"last_trades", r"trades_stream"],
    "ORDERS": [r"post_order", r"new_order", r"cancel_order", r"OrdersService"],
    "FILLS": [r"FillEvent", r"fill", r"trades"],
    "LATENCY_TELEMETRY": [r"latency", r"perf_counter", r"monotonic", r"round_trip"],
}

SEARCH_DIRS = [
    SRC / "finam_core",
    SRC / "scripts",
    SRC / "finam_proto",
]

def scan() -> dict[str, list[str]]:
    result = {k: [] for k in CAPABILITIES}
    files = []
    for d in SEARCH_DIRS:
        if d.exists():
            files.extend(d.rglob("*.py"))

    for path in files:
        try:
            text = path.read_text(errors="ignore")
        except Exception:
            continue

        rel = str(path.relative_to(ROOT))

        if rel.startswith("src/scripts/research/build_finam_api_capability_audit_v1.py"):
            continue

        if rel.startswith("src/scripts/research/build_microstructure_probe_v1.py"):
            continue

        for cap, patterns in CAPABILITIES.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    result[cap].append(rel)
                    break

    return result

def main() -> None:
    found = scan()

    print("=== FINAM API CAPABILITY AUDIT V1 ===")
    print()

    score = 0
    weights = {
        "CANDLES_OR_BARS": 15,
        "QUOTES_LAST": 10,
        "ORDER_BOOK": 20,
        "BEST_BID_ASK": 15,
        "TRADE_TAPE": 15,
        "ORDERS": 10,
        "FILLS": 10,
        "LATENCY_TELEMETRY": 5,
    }

    for cap in CAPABILITIES:
        hits = sorted(set(found[cap]))
        status = "FOUND" if hits else "NOT_FOUND"
        if hits:
            score += weights[cap]

        print(f"{cap}={status}")
        for item in hits[:12]:
            print(f"  {item}")
        if len(hits) > 12:
            print(f"  ... and {len(hits) - 12} more")
        print()

    print("=== SCALPING READINESS ===")
    print(f"score={score}/100")

    adapter_order_book = any(
        "src/finam_core/adapters" in item and "market_data" in item
        for item in found["ORDER_BOOK"]
    )

    adapter_best_bid_ask = any(
        "src/finam_core/adapters" in item and "market_data" in item
        for item in found["BEST_BID_ASK"]
    )

    if not found["ORDER_BOOK"] or not found["BEST_BID_ASK"]:
        verdict = "NOT_READY_FOR_SCALPING"
        reason = "order_book_or_best_bid_ask_not_confirmed"
    elif not adapter_order_book:
        verdict = "PROTO_ONLY"
        reason = "order_book_found_in_proto_but_not_adapter"
    elif not adapter_best_bid_ask:
        verdict = "PARTIAL"
        reason = "best_bid_ask_not_confirmed_in_market_data_adapter"
    elif not found["TRADE_TAPE"]:
        verdict = "PARTIAL"
        reason = "trade_tape_not_confirmed"
    elif not found["LATENCY_TELEMETRY"]:
        verdict = "PARTIAL"
        reason = "latency_not_measured"
    else:
        verdict = "READY_FOR_SCALPING_RESEARCH"
        reason = "microstructure_capabilities_detected_but_live_probe_required"

    print(f"verdict={verdict}")
    print(f"reason={reason}")

if __name__ == "__main__":
    main()
