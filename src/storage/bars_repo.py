# Репозиторий для хранения баров в PostgreSQL

from datetime import datetime
from typing import List, Tuple
import psycopg2


class BarsRepository:
    def __init__(self, conn):
        self.conn = conn

    def insert_bars(self, symbol: str, bars: List[Tuple[datetime, float, float]]):
        """
        bars: [(ts, close, volume)]
        """
        with self.conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO market_bars (symbol, ts, close, volume)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (symbol, ts) DO NOTHING
                """,
                [(symbol, ts, close, volume) for ts, close, volume in bars]
            )
        self.conn.commit()