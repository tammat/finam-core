# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from dataclasses import dataclass

import psycopg2
from dotenv import load_dotenv

load_dotenv(os.getenv("FINAM_ENV_FILE", "/opt/finam-core/deploy/env/.env"), override=False)


@dataclass(frozen=True)
class UnprotectedEntry:
    symbol: str
    side: str
    qty: float
    entry_order_id: str


def list_unprotected_entries(limit: int = 100) -> list[UnprotectedEntry]:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        return []

    with psycopg2.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT symbol, side, qty, entry_order_id
                FROM protective_order_links
                WHERE status = 'OPEN'
                  AND COALESCE(stop_order_id, '') = ''
                  AND COALESCE(take_order_id, '') = ''
                ORDER BY ts DESC
                LIMIT %s
                """,
                (int(limit),),
            )
            rows = cur.fetchall()

    return [
        UnprotectedEntry(
            symbol=str(symbol),
            side=str(side),
            qty=float(qty or 0.0),
            entry_order_id=str(entry_order_id),
        )
        for symbol, side, qty, entry_order_id in rows
    ]


def main() -> int:
    limit = int(os.getenv("PROTECTIVE_PLACEMENT_LIMIT", "100"))
    entries = list_unprotected_entries(limit=limit)

    print("PROTECTIVE_PLACEMENT_CHECK")
    print("mode=dry_run")
    print(f"auto_real_protective_enabled={os.getenv('AUTO_REAL_PROTECTIVE_ORDERS', '0')}")
    print(f"unprotected_entries={len(entries)}")

    for entry in entries:
        print(
            "PROTECTIVE_PLACEMENT_CANDIDATE "
            f"symbol={entry.symbol} side={entry.side} qty={entry.qty} "
            f"entry_order_id={entry.entry_order_id}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
