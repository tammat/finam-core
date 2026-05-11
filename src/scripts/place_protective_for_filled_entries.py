# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from dataclasses import dataclass

import psycopg2
from dotenv import load_dotenv

from finam_core.execution.protective_duplicate_gate import ProtectiveDuplicateGate

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



def resolve_last_price(symbol: str, entry_order_id: str | None = None) -> float | None:
    """Русский комментарий: цену ищем только в broker_order_snapshots; если её нет — возвращаем None."""
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        return None

    try:
        with psycopg2.connect(database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT raw
                    FROM broker_order_snapshots
                    WHERE symbol = %s
                      AND (%s IS NULL OR order_id = %s)
                    ORDER BY ts DESC
                    LIMIT 1
                    """,
                    (symbol, entry_order_id, entry_order_id),
                )
                row = cur.fetchone()
    except Exception as exc:
        print(f"PROTECTIVE_PRICE_LOOKUP_FAILED symbol={symbol} error={exc}", flush=True)
        return None

    if not row or not isinstance(row[0], dict):
        return None

    raw = row[0]
    for key in ("price", "avg_price", "average_price", "current_price", "last_price"):
        try:
            value = raw.get(key)
            if value is not None:
                return float(value)
        except Exception:
            pass

    return None


def calculate_stop_price(last_price: float, side: str, stop_pct: float) -> float:
    side_u = str(side or "").upper()

    if side_u == "BUY":
        return round(last_price * (1.0 - stop_pct), 2)

    return round(last_price * (1.0 + stop_pct), 2)


def main() -> int:
    limit = int(os.getenv("PROTECTIVE_PLACEMENT_LIMIT", "100"))
    entries = list_unprotected_entries(limit=limit)

    print("PROTECTIVE_PLACEMENT_CHECK")
    print("mode=dry_run")
    print(f"auto_real_protective_enabled={os.getenv('AUTO_REAL_PROTECTIVE_ORDERS', '0')}")
    print(f"unprotected_entries={len(entries)}")

    stop_pct = float(os.getenv("PROTECTIVE_STOP_PCT", "0.01"))

    for entry in entries:
        manual_reference_price = os.getenv("PROTECTIVE_REFERENCE_PRICE")
        if manual_reference_price:
            last_price = float(manual_reference_price)
        else:
            last_price = resolve_last_price(entry.symbol, entry.entry_order_id)

        stop_price = None
        if last_price is not None:
            stop_price = calculate_stop_price(
                last_price=last_price,
                side=entry.side,
                stop_pct=stop_pct,
            )

        duplicate_decision = ProtectiveDuplicateGate().check(
            entry_order_id=entry.entry_order_id,
            protective_type="stop",
        )

        print(
            "PROTECTIVE_PLACEMENT_CANDIDATE "
            f"symbol={entry.symbol} "
            f"side={entry.side} "
            f"qty={entry.qty} "
            f"entry_order_id={entry.entry_order_id} "
            f"last_price={last_price} "
            f"stop_pct={stop_pct} "
            f"dry_run_stop_price={stop_price} "
            f"duplicate_allowed={duplicate_decision.allowed} "
            f"duplicate_reason={duplicate_decision.reason}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
