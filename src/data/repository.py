class MarketBarRepository:

    def __init__(self, storage):
        self.storage = storage

    def upsert_many(self, rows):
        sql = """
        INSERT INTO market_bars
        (symbol, timeframe, ts, open, high, low, close, volume)
        VALUES (%(symbol)s, %(timeframe)s, %(ts)s,
                %(open)s, %(high)s, %(low)s,
                %(close)s, %(volume)s)
        ON CONFLICT (symbol, timeframe, ts)
        DO NOTHING;
        """
        self.storage.execute_many(sql, rows)

    def count(self, symbol, timeframe):
        sql = """
        SELECT count(*)
        FROM market_bars
        WHERE symbol = %s AND timeframe = %s;
        """
        return self.storage.fetch_one(sql, (symbol, timeframe))[0]