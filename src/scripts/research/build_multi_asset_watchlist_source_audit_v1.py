#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path


ROOTS = [
    Path("src/scripts/research"),
    Path("src/finam_core"),
]

NEEDLES = [
    "MULTI_ASSET_BREAKOUT_WATCH_V2",
    "MULTI_ASSET_BREAKOUT_SIGNAL_QUALITY_OBSERVATION_V1",
    "BRQ6@RTSX",
    "NGN6@RTSX",
    "GDU6@RTSX",
    "PRIMARY_WATCH",
    "INTRADAY_WATCH",
    "RUNTIME_EQUITY_WATCH",
    "breakout_ready",
    "ready_rows",
]


def score_file(path: Path, text: str) -> int:
    score = 0
    for n in NEEDLES:
        if n in text:
            score += 1
    if "analytics_multi_asset_breakout_row_v1" in text:
        score += 3
    if "market_bars" in text:
        score += 2
    if "rows_total" in text:
        score += 2
    if "universe" in text.lower():
        score += 2
    return score


def main() -> int:
    print("=== MULTI ASSET WATCHLIST SOURCE AUDIT V1 ===")
    print("mode=read_only_source_audit")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print("orders_create=0")
    print("execution_intents_create=0")

    candidates: list[tuple[int, Path, list[str]]] = []

    for root in ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue

            score = score_file(path, text)
            if score <= 0:
                continue

            hits = [n for n in NEEDLES if n in text]
            candidates.append((score, path, hits))

    candidates.sort(key=lambda x: (-x[0], str(x[1])))

    print()
    print("WATCHLIST_SOURCE_CANDIDATES")
    for score, path, hits in candidates[:30]:
        print(
            "WATCHLIST_SOURCE_ROW "
            f"score={score} path={path} hits={','.join(hits)}"
        )

    top = candidates[0] if candidates else None

    print()
    print("WATCHLIST_SOURCE_AUDIT_SUMMARY")
    print(f"candidates_total={len(candidates)}")
    if top:
        print(f"top_path={top[1]}")
        print(f"top_score={top[0]}")
        print("VERDICT=MULTI_ASSET_WATCHLIST_SOURCE_AUDIT_CANDIDATE_FOUND")
    else:
        print("top_path=NONE")
        print("top_score=0")
        print("VERDICT=MULTI_ASSET_WATCHLIST_SOURCE_AUDIT_NO_CANDIDATE")

    print("MULTI_ASSET_WATCHLIST_SOURCE_AUDIT_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
