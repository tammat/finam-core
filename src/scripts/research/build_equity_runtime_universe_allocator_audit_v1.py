#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import re
from pathlib import Path
import psycopg2
import psycopg2.extras

TARGETS = ["EUTR@MISX", "SBERP@MISX", "VTBR@MISX", "SFIN@MISX"]

SEARCH_TERMS = [
    "runtime_active_universe",
    "RuntimeUniverseAllocator",
    "dynamic_watchlist",
    "VOLATILITY_BREAKOUT_EQUITY",
    "is_enabled",
    "disabled_at",
    "disable_reason",
    "runtime allocator",
    "allocator",
]

ROOTS = [Path("src"), Path("scripts")]


def scan_sources():
    hits = []
    for root in ROOTS:
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if p.suffix not in {".py", ".sh", ".sql"}:
                continue
            try:
                text = p.read_text(errors="ignore")
            except Exception:
                continue
            file_hits = []
            for i, line in enumerate(text.splitlines(), start=1):
                for term in SEARCH_TERMS:
                    if term in line:
                        file_hits.append({
                            "line": i,
                            "term": term,
                            "text": line.strip()[:240],
                        })
            if file_hits:
                score = 0
                joined = " ".join(h["term"] for h in file_hits)
                if "RuntimeUniverseAllocator" in joined:
                    score += 5
                if "runtime_active_universe" in joined:
                    score += 4
                if "dynamic_watchlist" in joined:
                    score += 3
                if "VOLATILITY_BREAKOUT_EQUITY" in joined:
                    score += 2
                if "allocator" in str(p):
                    score += 2
                hits.append({
                    "path": str(p),
                    "score": score,
                    "hit_count": len(file_hits),
                    "terms": sorted(set(h["term"] for h in file_hits)),
                    "sample_hits": file_hits[:20],
                })
    return sorted(hits, key=lambda x: (-x["score"], x["path"]))[:30]


def main() -> int:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("ERROR=DATABASE_URL_NOT_SET")
        return 1

    rows = []

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            for symbol in TARGETS:
                cur.execute("""
                    select
                        symbol,
                        strategy,
                        timeframe,
                        regime,
                        score,
                        priority,
                        is_enabled,
                        source,
                        last_seen_at,
                        updated_at,
                        disabled_at,
                        disable_reason
                    from runtime_active_universe
                    where symbol = %s
                    order by updated_at desc nulls last
                    limit 5
                """, (symbol,))
                runtime_rows = [dict(r) for r in cur.fetchall()]

                cur.execute("""
                    select count(*)::int as bars, max(ts) as last_ts
                    from market_bars
                    where symbol = %s and timeframe = 'M5'
                """, (symbol,))
                bars = dict(cur.fetchone())

                cur.execute("""
                    select count(*)::int as history_rows, max(created_at) as last_history
                    from analytics_multi_asset_breakout_row_v1
                    where symbol = %s
                """, (symbol,))
                hist = dict(cur.fetchone())

                diagnosis = "UNKNOWN"
                if len(runtime_rows) == 0:
                    diagnosis = "MISSING_FROM_RUNTIME_ACTIVE_UNIVERSE"
                elif not any(r.get("is_enabled") for r in runtime_rows):
                    diagnosis = "PRESENT_BUT_DISABLED"
                elif int(bars.get("bars") or 0) == 0:
                    diagnosis = "RUNTIME_PRESENT_BUT_NO_M5_BARS"
                else:
                    diagnosis = "RUNTIME_AND_BARS_OK_RECHECK_WATCHER"

                rows.append({
                    "symbol": symbol,
                    "diagnosis": diagnosis,
                    "runtime_rows": runtime_rows,
                    "m5_bars": int(bars.get("bars") or 0),
                    "m5_last_ts": None if bars.get("last_ts") is None else str(bars.get("last_ts")),
                    "history_rows": int(hist.get("history_rows") or 0),
                    "history_last_seen": None if hist.get("last_history") is None else str(hist.get("last_history")),
                })

    summary = {}
    for r in rows:
        summary[r["diagnosis"]] = summary.get(r["diagnosis"], 0) + 1

    out = {
        "verdict": "EQUITY_RUNTIME_UNIVERSE_ALLOCATOR_AUDIT_READY",
        "mode": "read_only",
        "db_update": 0,
        "runtime_changed": 0,
        "execution_changed": 0,
        "telegram_send": 0,
        "targets_total": len(TARGETS),
        "summary": summary,
        "rows": rows,
        "source_hits": scan_sources(),
    }

    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    print("VERDICT=EQUITY_RUNTIME_UNIVERSE_ALLOCATOR_AUDIT_READY")
    print("TEST_EQUITY_RUNTIME_UNIVERSE_ALLOCATOR_AUDIT_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
