import psycopg
from domain.fill_event import FillEvent


class PostgresStorage:
    def __init__(self, dsn: str):
        self.dsn = dsn

    def append_fill(self, fill: FillEvent):
        """
        Append fill to Postgres.
        Idempotent by fill_id.
        """
        with psycopg.connect(self.dsn, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO fills
                    (fill_id, ts, symbol, side, qty, price, commission, order_id)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (fill_id) DO NOTHING
                    """,
                    (
                        fill.fill_id,
                        fill.timestamp,
                        fill.symbol,
                        fill.side,
                        fill.quantity,
                        fill.price,
                        fill.commission,
                        fill.order_id,
                    ),
                )

    def load_fills(self, symbol: str):
        """
        Stream fills by symbol ordered by timestamp.
        """
        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT fill_id, ts, symbol, side,
                           qty, price, commission, order_id
                    FROM fills
                    WHERE symbol = %s
                    ORDER BY ts
                    """,
                    (symbol,),
                )

                for row in cur.fetchall():
                    yield FillEvent(
                        fill_id=row[0],
                        timestamp=row[1],
                        symbol=row[2],
                        side=row[3],
                        quantity=row[4],
                        price=row[5],
                        commission=row[6],
                        order_id=row[7],
                    )