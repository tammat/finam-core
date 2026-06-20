#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

INDEX_ALIASES = {
    "IMOEX": ["IMOEX", "IMOEX@MISX", "MOEX"],
    "RTSI": ["RTSI", "RTSI@MISX"],
}

SEARCH_TERMS = [
    "IMOEX",
    "RTSI",
    "index",
    "indices",
    "moex",
    "market_bars",
    "candles",
]

SCAN_ROOTS = ["src/scripts", "src/finam_core", "deploy/systemd"]


def scan_files() -> list[dict]:
    hits = []
    for root in SCAN_ROOTS:
        base = Path(root)
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if not p.is_file():
                continue
            if p.suffix in {".pyc", ".png", ".jpg", ".jpeg", ".db", ".sqlite"}:
                continue
            try:
                text = p.read_text(errors="ignore")
            except Exception:
                continue

            file_hits = []
            lower = text.lower()
            for term in SEARCH_TERMS:
                if term.lower() in lower:
                    file_hits.append(term)

            if file_hits:
                hits.append({
                    "path": str(p),
                    "terms": sorted(set(file_hits)),
                    "score": len(set(file_hits)),
                })

    hits.sort(key=lambda r: (r["score"], r["path"]), reverse=True)
    return hits[:40]


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL_NOT_SET")

    out = {
        "verdict": "INDEX_MARKET_DATA_BACKFILL_AUDIT_READY",
        "mode": "read_only",
        "db_update": 0,
        "runtime_changed": 0,
        "execution_changed": 0,
        "telegram_send": 0,
        "index_rows": [],
        "candidate_loader_files": scan_files(),
        "diagnosis": "UNKNOWN",
        "next_required": "REVIEW",
    }

    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            for index_name, aliases in INDEX_ALIASES.items():
                for alias in aliases:
                    for tf in ["M1", "M5", "H1", "D1"]:
                        cur.execute(
                            """
                            select
                                %s as index_name,
                                %s as symbol_checked,
                                %s as timeframe_checked,
                                count(*)::int as bars,
                                min(ts) as first_ts,
                                max(ts) as last_ts
                            from market_bars
                            where symbol = %s
                              and timeframe = %s
                            """,
                            (index_name, alias, tf, alias, tf),
                        )
                        out["index_rows"].append(dict(cur.fetchone()))

    total_bars = sum(int(r["bars"] or 0) for r in out["index_rows"])
    has_imoex = any(r["index_name"] == "IMOEX" and int(r["bars"] or 0) > 0 for r in out["index_rows"])
    has_rtsi = any(r["index_name"] == "RTSI" and int(r["bars"] or 0) > 0 for r in out["index_rows"])

    if has_imoex and has_rtsi:
        diagnosis = "INDEX_MARKET_BARS_EXIST"
        next_required = "INDEX_CONTEXT_WATCH_V1"
    elif has_imoex and not has_rtsi:
        diagnosis = "IMOEX_EXISTS_RTSI_MISSING"
        next_required = "RTSI_BACKFILL_REQUIRED"
    elif not has_imoex and has_rtsi:
        diagnosis = "RTSI_EXISTS_IMOEX_MISSING"
        next_required = "IMOEX_BACKFILL_REQUIRED"
    else:
        diagnosis = "INDEX_MARKET_BARS_ABSENT"
        next_required = "MOEX_INDEX_BACKFILL_V1"

    out["diagnosis"] = diagnosis
    out["next_required"] = next_required
    out["total_index_bars"] = total_bars

    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
    print(f"DIAGNOSIS={diagnosis}")
    print(f"NEXT_REQUIRED={next_required}")
    print("VERDICT=INDEX_MARKET_DATA_BACKFILL_AUDIT_READY")
    print("TEST_INDEX_MARKET_DATA_BACKFILL_AUDIT_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
