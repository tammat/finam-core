import psycopg2
import numpy as np
from pathlib import Path


def _normalize(value):
    if isinstance(value, np.generic):
        return value.item()
    return value


class PostgresStorage:

    def __init__(self, dsn: str):
        self.conn = psycopg2.connect(dsn)
        self.conn.autocommit = False

    # ---------------- MIGRATIONS ----------------

    def apply_migrations(self):
        migrations_path = Path(__file__).parent / "migrations.sql"
        print(f"Applying migrations from: {migrations_path}")

        with open(migrations_path, "r") as f:
            sql = f.read()

        with self.conn.cursor() as cur:
            cur.execute(sql)

        self.conn.commit()

    # ---------------- SIGNALS ----------------

    def log_signal(self, event):
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO signals (event_id, correlation_id, symbol, signal_type, strength, ts)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    getattr(event, "event_id", None),
                    getattr(event, "correlation_id", None),
                    event.symbol,
                    event.signal_type,
                    float(event.strength) if getattr(event, "strength", None) is not None else None,
                    event.timestamp,
                ),
            )
        self.conn.commit()
    def log_fill(self, event):
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO fills (symbol, side, quantity, price, ts)
                VALUES (%s, %s, %s, %s, NOW())
                """,
                (
                    _normalize(event.symbol),
                    _normalize(event.side),
                    _normalize(event.quantity),
                    _normalize(event.price),
                ),
            )
        self.conn.commit()

    # ---------------- TRADES ----------------

    def log_trade(self, trade):
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO trades (symbol, side, quantity, price, ts)
                VALUES (%s, %s, %s, %s, NOW())
                """,
                (
                    _normalize(trade.symbol),
                    _normalize(trade.side),
                    _normalize(trade.quantity),
                    _normalize(trade.price),
                ),
            )
        self.conn.commit()

    # ---------------- CLOSE ----------------

    def close(self):
        if self.conn:
            self.conn.close()

    def last_price(self, symbol: str) -> float:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT price
                FROM market_data
                WHERE symbol = %s
                ORDER BY ts DESC LIMIT 1
                """,
                (symbol,),
            )
            row = cur.fetchone()

        if row:
            return float(row[0])

        return 0.0

    def log_market_price(
            self,
            symbol: str,
            close_price: float,
            volume: float,
            timestamp,
    ):
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO market_data (symbol, price, volume, ts)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    symbol,
                    float(close_price),
                    float(volume),
                    timestamp,
                ),
            )
        self.conn.commit()

    def log_features(self, symbol: str, features: dict, timestamp):
        if not features:
            return

        with self.conn.cursor() as cur:
            for name, value in features.items():
                cur.execute(
                    """
                    INSERT INTO signal_features (symbol, feature_name, feature_value, ts)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (
                        symbol,
                        name,
                        float(value),
                        timestamp,
                    ),
                )
        self.conn.commit()