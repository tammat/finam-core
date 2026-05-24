from __future__ import annotations

import os

import psycopg

from finam_core.analytics.closed_trade_enrichment import (
    calculate_closed_trade_quality,
    normalize_root_symbol,
)


def main() -> None:
    """Русский комментарий: обогащает closed_trades расчетными полями v2."""
    database_url = os.environ["DATABASE_URL"]

    select_sql = """
    SELECT
        id,
        symbol,
        side,
        entry_price::float,
        exit_price::float
    FROM closed_trades
    ORDER BY id;
    """

    update_sql = """
    UPDATE closed_trades
    SET
        root_symbol = %(root_symbol)s,
        mae = %(mae)s,
        mfe = %(mfe)s,
        realized_rr = %(realized_rr)s,
        quality_score = %(quality_score)s
    WHERE id = %(id)s;
    """

    updated = 0

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(select_sql)
            rows = cur.fetchall()

            for row in rows:
                trade_id, symbol, side, entry_price, exit_price = row

                q = calculate_closed_trade_quality(
                    side=str(side),
                    entry_price=float(entry_price),
                    exit_price=float(exit_price),
                )

                cur.execute(
                    update_sql,
                    {
                        "id": trade_id,
                        "root_symbol": normalize_root_symbol(str(symbol)),
                        "mae": q.mae,
                        "mfe": q.mfe,
                        "realized_rr": q.realized_rr,
                        "quality_score": q.quality_score,
                    },
                )
                updated += 1

        conn.commit()

    print(f"CLOSED_TRADES_V2_ENRICH_OK updated={updated}", flush=True)


if __name__ == "__main__":
    main()
