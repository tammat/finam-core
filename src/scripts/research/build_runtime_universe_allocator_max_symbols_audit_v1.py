#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
from pathlib import Path
import psycopg2
import psycopg2.extras

TARGETS = ["EUTR@MISX", "SBERP@MISX", "VTBR@MISX", "SFIN@MISX"]
LIMITS = [5, 8, 10]


def scan_max_symbols():
    hits = []
    for root in [Path("src"), Path("scripts"), Path("deploy")]:
        if not root.exists():
            continue
        for p in root.rglob("*"):
            if p.suffix not in {".py", ".sh", ".service", ".timer", ".env"}:
                continue
            try:
                text = p.read_text(errors="ignore")
            except Exception:
                continue
            for i, line in enumerate(text.splitlines(), start=1):
                if "max_symbols" in line or "MAX_SYMBOLS" in line or "RUNTIME_MAX" in line:
                    hits.append({"path": str(p), "line": i, "text": line.strip()[:240]})
    return hits


def main() -> int:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("ERROR=DATABASE_URL_NOT_SET")
        return 1

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                select
                    symbol,
                    strategy,
                    'M5'::text as timeframe,
                    score::numeric as score,
                    priority,
                    source
                from dynamic_watchlist
                where symbol like '%@MISX'
                order by priority desc nulls last, score desc nulls last, symbol
            """)
            dyn = [dict(r) for r in cur.fetchall()]

    simulations = []
    for limit in LIMITS:
        selected = dyn[:limit]
        selected_symbols = {r["symbol"] for r in selected}
        simulations.append({
            "max_symbols": limit,
            "selected_total": len(selected),
            "selected_symbols": [r["symbol"] for r in selected],
            "target_inclusion": {
                symbol: symbol in selected_symbols
                for symbol in TARGETS
            },
        })

    out = {
        "verdict": "RUNTIME_UNIVERSE_ALLOCATOR_MAX_SYMBOLS_AUDIT_READY",
        "mode": "read_only",
        "db_update": 0,
        "runtime_changed": 0,
        "execution_changed": 0,
        "telegram_send": 0,
        "dynamic_equity_rows": len(dyn),
        "target_symbols": TARGETS,
        "current_top10": dyn[:10],
        "simulations": simulations,
        "max_symbols_source_hits": scan_max_symbols(),
    }

    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    print("VERDICT=RUNTIME_UNIVERSE_ALLOCATOR_MAX_SYMBOLS_AUDIT_READY")
    print("TEST_RUNTIME_UNIVERSE_ALLOCATOR_MAX_SYMBOLS_AUDIT_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
