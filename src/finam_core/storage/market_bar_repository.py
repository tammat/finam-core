from __future__ import annotations

from typing import Iterable, Dict, Any


class MarketBarRepository:
    """
    UPSERT OHLCV bars into market_bars.
    Expects PostgresStorage with .execute(sql, params) or .execute_many(sql, params_list).
    """

    def __init__(self, storage):
        self.storage = storage

    def upsert_many(self, rows: Iterable[Dict[str, Any]]) -> int:
        rows = list(rows)
        if not rows:
            return 0

        sql = """
        INSERT INTO market_bars
            (symbol, timeframe, ts, open, high, low, close, volume, source)
        VALUES
            (%(symbol)s, %(timeframe)s, %(ts)s, %(open)s, %(high)s, %(low)s, %(close)s, %(volume)s, %(source)s)
        ON CONFLICT (symbol, timeframe, ts)
        DO UPDATE SET
            open   = EXCLUDED.open,
            high   = EXCLUDED.high,
            low    = EXCLUDED.low,
            close  = EXCLUDED.close,
            volume = EXCLUDED.volume,
            source = EXCLUDED.source
        ;
        """

        # PostgresStorage у тебя может быть разный — поддержим оба случая
        exec_many = getattr(self.storage, "execute_many", None)
        if callable(exec_many):
            exec_many(sql, rows)
            return len(rows)

        exec_one = getattr(self.storage, "execute", None)
        if callable(exec_one):
            for r in rows:
                exec_one(sql, r)
            return len(rows)

        raise AttributeError("PostgresStorage must provide execute_many(sql, params_list) or execute(sql, params)")
