# -*- coding: utf-8 -*-

from __future__ import annotations

import os
import psycopg2

from finam_core.notifications.telegram_notifier import TelegramNotifier


def main() -> None:
    conn = psycopg2.connect(
        dbname=os.getenv("PGDATABASE", "finam_core"),
        user=os.getenv("PGUSER") or None,
        host=os.getenv("PGHOST") or None,
        port=os.getenv("PGPORT") or None,
        password=os.getenv("PGPASSWORD") or None,
    )

    with conn.cursor() as cur:
        cur.execute("""
            SELECT symbol, trades, wins, losses,
                   ROUND(net_pnl::numeric, 2),
                   ROUND(expectancy::numeric, 2),
                   ROUND(profit_factor::numeric, 2),
                   ROUND(winrate::numeric, 2)
            FROM grafana_closed_trade_summary
            ORDER BY net_pnl DESC;
        """)
        rows = cur.fetchall()

    lines = [
        "📊 Итоги стратегии за день",
        "",
        "Paper-контур. Реальные заявки не выставлялись.",
        "",
    ]

    if not rows:
        lines.append("Сегодня закрытых paper-сделок нет.")
    else:
        for r in rows:
            symbol, trades, wins, losses, net_pnl, expectancy, pf, winrate = r
            lines.extend([
                f"Инструмент: {symbol}",
                f"Сделок: {trades} | Win/Loss: {wins}/{losses}",
                f"Net PnL: {net_pnl}",
                f"Expectancy: {expectancy}",
                f"Profit Factor: {pf}",
                f"Winrate: {winrate}%",
                "",
            ])

    TelegramNotifier().send("\n".join(lines))


if __name__ == "__main__":
    main()
