# src/scripts/show_trade_journal.py

from __future__ import annotations

import os
import psycopg2

from finam_core.analytics.trade_journal import TradeJournal, TradeRow


def main() -> None:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError("DATABASE_URL is required")

    limit = int(os.getenv("TRADE_JOURNAL_LIMIT", "200"))

    with psycopg2.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT symbol, side, qty, price, commission
                FROM trades
                ORDER BY id ASC
                LIMIT %s
                """,
                (limit,),
            )
            rows = [
                TradeRow(
                    symbol=r[0],
                    side=r[1],
                    qty=float(r[2] or 0),
                    price=float(r[3] or 0),
                    commission=float(r[4] or 0),
                )
                for r in cur.fetchall()
            ]

    summary = TradeJournal().summarize(rows)

    print("ЖУРНАЛ СДЕЛОК")
    print("=" * 50)
    print(f"Всего сделок          : {summary.trades_count}")
    print(f"Закрытых циклов       : {summary.closed_cycles}")
    print(f"Прибыльных циклов     : {summary.wins}")
    print(f"Убыточных циклов      : {summary.losses}")
    print(f"Winrate               : {summary.winrate:.2%}")
    print(f"Итоговый PnL          : {summary.total_pnl:.4f}")
    print(f"Средний PnL на цикл   : {summary.avg_pnl:.4f}")


if __name__ == "__main__":
    main()
