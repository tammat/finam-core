from __future__ import annotations

import os
import psycopg2
from psycopg2.extras import RealDictCursor

from finam_core.portfolio.positions_provider import BrokerPosition


class LatestRealPositionsProvider:
    def __init__(self, dsn: str | None = None):
        self.dsn = (
            dsn
            or os.getenv("FINAM_DSN")
            or os.getenv("POSTGRES_DSN")
            or "dbname=finam_core user=finam password=finam host=localhost port=5432"
        )

    def get_positions(self) -> list[BrokerPosition]:
        sql = """
        select symbol, qty, avg_price
        from real_position_snapshots
        where ts = (select max(ts) from real_position_snapshots)
          and qty <> 0
        order by symbol
        """

        with psycopg2.connect(self.dsn) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(sql)
                rows = cur.fetchall()

        return [
            BrokerPosition(
                symbol=row["symbol"],
                qty=float(row["qty"]),
                avg_price=float(row["avg_price"]) if row["avg_price"] is not None else None,
                raw=dict(row),
            )
            for row in rows
        ]
