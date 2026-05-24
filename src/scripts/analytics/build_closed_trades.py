from __future__ import annotations

import os
from collections import defaultdict

import psycopg

from finam_core.analytics.closed_trade_engine import Fill, build_closed_trades_fifo


def load_fills(database_url: str) -> list[Fill]:
    """Русский комментарий: загружаем валидные fills из trades."""
    sql = """
    SELECT
        symbol,
        side,
        qty::float,
        price::float,
        COALESCE(commission, 0)::float,
        COALESCE(NULLIF(strategy, ''), 'unknown') AS strategy,
        COALESCE(NULLIF(timeframe, ''), 'unknown') AS timeframe,
        COALESCE(ts, created_at) AS ts
    FROM trades
    WHERE COALESCE(is_invalid, false) = false
      AND symbol IS NOT NULL
      AND side IS NOT NULL
      AND qty IS NOT NULL
      AND price IS NOT NULL
    ORDER BY COALESCE(ts, created_at), id;
    """

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()

    return [
        Fill(
            symbol=str(row[0]),
            side=str(row[1]),
            qty=float(row[2]),
            price=float(row[3]),
            commission=float(row[4]),
            strategy=str(row[5]),
            timeframe=str(row[6]),
            ts=row[7],
        )
        for row in rows
    ]


def build_grouped_closed_trades(fills: list[Fill]):
    """
    Русский комментарий:
    Закрытые сделки собираем отдельно по symbol + strategy + timeframe,
    чтобы FIFO не смешивал разные стратегии и инструменты.
    """
    grouped: dict[tuple[str, str, str], list[Fill]] = defaultdict(list)

    for fill in fills:
        grouped[(fill.symbol, fill.strategy, fill.timeframe)].append(fill)

    closed = []
    for group_fills in grouped.values():
        closed.extend(build_closed_trades_fifo(group_fills))

    return closed


def save_closed_trades(database_url: str, closed_trades) -> int:
    """Русский комментарий: пересобираем closed_trades как materialized analytics snapshot."""
    insert_sql = """
    INSERT INTO closed_trades (
        symbol,
        strategy,
        timeframe,
        side,
        qty,
        entry_price,
        exit_price,
        gross_pnl,
        commission,
        net_pnl,
        opened_at,
        closed_at,
        holding_seconds
    )
    VALUES (
        %(symbol)s,
        %(strategy)s,
        %(timeframe)s,
        %(side)s,
        %(qty)s,
        %(entry_price)s,
        %(exit_price)s,
        %(gross_pnl)s,
        %(commission)s,
        %(net_pnl)s,
        %(opened_at)s,
        %(closed_at)s,
        %(holding_seconds)s
    );
    """

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute("TRUNCATE closed_trades;")

            for trade in closed_trades:
                cur.execute(
                    insert_sql,
                    {
                        "symbol": trade.symbol,
                        "strategy": trade.strategy,
                        "timeframe": trade.timeframe,
                        "side": trade.side,
                        "qty": trade.qty,
                        "entry_price": trade.entry_price,
                        "exit_price": trade.exit_price,
                        "gross_pnl": trade.gross_pnl,
                        "commission": trade.commission,
                        "net_pnl": trade.net_pnl,
                        "opened_at": trade.opened_at,
                        "closed_at": trade.closed_at,
                        "holding_seconds": trade.holding_seconds,
                    },
                )

        conn.commit()

    return len(closed_trades)


def main() -> None:
    database_url = os.environ["DATABASE_URL"]

    fills = load_fills(database_url)
    closed = build_grouped_closed_trades(fills)
    saved = save_closed_trades(database_url, closed)

    print(
        "CLOSED_TRADES_BUILD_OK "
        f"fills={len(fills)} closed_trades={saved}",
        flush=True,
    )


if __name__ == "__main__":
    main()
