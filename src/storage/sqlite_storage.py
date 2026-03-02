import sqlite3
from storage.base_storage import BaseStorage


class SQLiteStorage(BaseStorage):

    def __init__(self, path=":memory:"):
        self.conn = sqlite3.connect(path)
        self._init_schema()

    def _init_schema(self):
        cur = self.conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS fills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT,
                side TEXT,
                qty REAL,
                price REAL
            )
        """)

        self.conn.commit()

    # ---- required by BaseStorage ----

    def append_fill(self, fill):
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO fills (symbol, side, qty, price) VALUES (?, ?, ?, ?)",
            (fill.symbol, fill.side, fill.qty, fill.price),
        )
        self.conn.commit()

    def load_fills(self):
        cur = self.conn.cursor()
        cur.execute("SELECT symbol, side, qty, price FROM fills")
        rows = cur.fetchall()

        return [
            {
                "symbol": r[0],
                "side": r[1],
                "qty": r[2],
                "price": r[3],
            }
            for r in rows
        ]

    def close(self):
        self.conn.close()