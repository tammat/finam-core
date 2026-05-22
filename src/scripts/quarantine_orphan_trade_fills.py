from __future__ import annotations

import argparse
import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url


def migrate(cur) -> None:
    cur.execute("""
        ALTER TABLE trades
        ADD COLUMN IF NOT EXISTS is_invalid BOOLEAN NOT NULL DEFAULT FALSE;

        ALTER TABLE trades
        ADD COLUMN IF NOT EXISTS invalid_reason TEXT NOT NULL DEFAULT '';

        CREATE INDEX IF NOT EXISTS idx_trades_invalid_symbol
        ON trades(symbol, trade_source, is_invalid);
    """)


def quarantine_symbol(cur, symbol: str, trade_source: str) -> tuple[int, int]:
    cur.execute("""
        SELECT id, side, qty
        FROM trades
        WHERE symbol = %s
          AND trade_source = %s
          AND COALESCE(is_invalid, FALSE) = FALSE
        ORDER BY ts, id
    """, (symbol, trade_source))

    rows = cur.fetchall()

    inventory = 0.0
    invalid_ids: list[int] = []

    for trade_id, side, qty in rows:
        qty = float(qty or 0.0)
        side = str(side or "").upper()

        if side == "BUY":
            inventory += qty
            continue

        if side == "SELL":
            if inventory + 1e-9 >= qty:
                inventory -= qty
            else:
                invalid_ids.append(int(trade_id))
            continue

    if invalid_ids:
        cur.execute("""
            UPDATE trades
            SET is_invalid = TRUE,
                invalid_reason = 'orphan_sell_without_position'
            WHERE id = ANY(%s)
        """, (invalid_ids,))

    return len(rows), len(invalid_ids)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", required=True)
    parser.add_argument("--trade-source", default="paper")
    parser.add_argument("--migrate", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    symbols = [x.strip() for x in args.symbols.split(",") if x.strip()]

    total_rows = 0
    total_invalid = 0

    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cur:
            if args.migrate:
                migrate(cur)

            for symbol in symbols:
                rows, invalid = quarantine_symbol(cur, symbol, args.trade_source)
                total_rows += rows
                total_invalid += invalid

                print(
                    "TRADE_HYGIENE_ORPHAN_FILLS "
                    f"symbol={symbol} rows={rows} invalid={invalid}",
                    flush=True,
                )

            if args.apply:
                conn.commit()
            else:
                conn.rollback()

    print(
        "TRADE_HYGIENE_ORPHAN_FILLS_SUMMARY "
        f"symbols={len(symbols)} rows={total_rows} invalid={total_invalid} "
        f"applied={args.apply}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
