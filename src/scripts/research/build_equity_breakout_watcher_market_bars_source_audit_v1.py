#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import re
import sys
from pathlib import Path

TARGET_TERMS = [
    "market_bars",
    "analytics_multi_asset_breakout_row_v1",
    "NO_ENOUGH_BARS",
    "RUNTIME_EQUITY_WATCH",
    "VOLATILITY_BREAKOUT_EQUITY",
    "runtime_active_universe",
    "build_multi_asset_breakout",
    "multi_asset_breakout",
]

SEARCH_ROOTS = [
    Path("src"),
    Path("scripts"),
]


def scan_file(path: Path) -> dict:
    try:
        text = path.read_text(errors="ignore")
    except Exception as exc:
        return {"path": str(path), "error": str(exc), "hits": []}

    hits = []
    lines = text.splitlines()

    for i, line in enumerate(lines, start=1):
        for term in TARGET_TERMS:
            if term in line:
                hits.append(
                    {
                        "line": i,
                        "term": term,
                        "text": line.strip()[:300],
                    }
                )

    return {
        "path": str(path),
        "hits": hits,
    }


def main() -> int:
    files = []

    for root in SEARCH_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.suffix not in {".py", ".sh", ".sql"}:
                continue
            result = scan_file(path)
            if result.get("hits"):
                files.append(result)

    key_files = []
    for item in files:
        path = item["path"]
        terms = sorted({h["term"] for h in item["hits"]})
        hit_count = len(item["hits"])

        score = 0
        if "market_bars" in terms:
            score += 3
        if "NO_ENOUGH_BARS" in terms:
            score += 3
        if "RUNTIME_EQUITY_WATCH" in terms:
            score += 2
        if "VOLATILITY_BREAKOUT_EQUITY" in terms:
            score += 2
        if "multi_asset_breakout" in path:
            score += 2
        if "build_multi_asset_breakout" in path:
            score += 2

        key_files.append(
            {
                "path": path,
                "score": score,
                "hit_count": hit_count,
                "terms": terms,
                "sample_hits": item["hits"][:20],
            }
        )

    key_files.sort(key=lambda x: (-x["score"], x["path"]))

    diagnosis = "SOURCE_AUDIT_READY_REVIEW_REQUIRED"
    if key_files:
        top_terms = set(key_files[0]["terms"])
        if "NO_ENOUGH_BARS" in top_terms and "market_bars" not in top_terms:
            diagnosis = "LIKELY_WATCHER_NOT_READING_MARKET_BARS"
        elif "NO_ENOUGH_BARS" in top_terms and "market_bars" in top_terms:
            diagnosis = "LIKELY_MARKET_BARS_QUERY_FILTER_REVIEW_REQUIRED"

    out = {
        "verdict": "EQUITY_BREAKOUT_WATCHER_MARKET_BARS_SOURCE_AUDIT_READY",
        "db_update": 0,
        "runtime_changed": 0,
        "execution_changed": 0,
        "telegram_send": 0,
        "files_scanned": sum(1 for root in SEARCH_ROOTS if root.exists() for _ in root.rglob("*")),
        "matched_files": len(files),
        "diagnosis": diagnosis,
        "top_files": key_files[:20],
    }

    print(json.dumps(out, ensure_ascii=False, indent=2))
    print("VERDICT=EQUITY_BREAKOUT_WATCHER_MARKET_BARS_SOURCE_AUDIT_READY")
    print("TEST_EQUITY_BREAKOUT_WATCHER_MARKET_BARS_SOURCE_AUDIT_V1_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
