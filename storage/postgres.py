import json
import os
import psycopg2


class PostgresStorage:
    def __init__(self, dsn=None):
        self.dsn = dsn or os.getenv("FINAM_DSN", "")
        self.offline = not bool(self.dsn)

        self.conn = None

        if not self.offline:
            self.conn = psycopg2.connect(self.dsn)
            self.conn.autocommit = True
            self._apply_migrations()

    # ------------------------
    # MIGRATIONS
    # ------------------------

    def _apply_migrations(self):
        base_dir = os.path.dirname(__file__)
        path = os.path.join(base_dir, "migrations.sql")

        print("Applying migrations from:", path)

        if not os.path.exists(path):
            raise FileNotFoundError("migrations.sql not found")

        with open(path, "r", encoding="utf-8") as f:
            sql = f.read()

        with self.conn.cursor() as cur:
            cur.execute(sql)

    # ------------------------
    # PRICE RESOLVER
    # ------------------------

    def last_price(self, symbol):
        if self.offline:
            return 0.0

        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT close
                FROM historical_prices
                WHERE symbol = %s
                ORDER BY ts DESC
                LIMIT 1
            """, (symbol,))

            row = cur.fetchone()

        if not row:
            return 0.0

        return row[0]

    def log_market(self, event):
        if self.offline:
            return

        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO market_ticks(symbol, price, volume, ts)
                VALUES (%s, %s, %s, %s)
            """, (event.symbol, event.price, event.volume, event.timestamp))

    def log_signal(self, event):
        if self.offline:
            return

        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO signals(symbol, signal_type, strength, ts)
                VALUES (%s, %s, %s, %s)
            """, (event.symbol, event.signal_type, event.strength, event.timestamp))

    def log_order(self, event):
        if self.offline:
            return

        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO orders(order_id, symbol, side, quantity, status, ts)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (order_id)
                DO UPDATE SET
                    status = EXCLUDED.status,
                    quantity = EXCLUDED.quantity
            """, (
                event.event_id,
                event.symbol,
                event.side,
                event.quantity,
                event.status.value,
                event.timestamp,
            ))
    def log_trade(self, event):
        if self.offline:
            return

        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO trades(symbol, side, quantity, price, ts)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                event.symbol,
                event.side,
                event.quantity,
                event.price,
                event.timestamp,
            ))

    def log_risk_event(self, event):
        if self.offline:
            return

        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO risk_events(symbol, reason, ts)
                VALUES (%s, %s, %s)
            """, (
                event.symbol,
                event.reason,
                event.timestamp,
            ))
    def log_features(self, symbol, timestamp, features: dict):
        if self.offline:
            return

        with self.conn.cursor() as cur:
            for name, value in features.items():
                cur.execute("""
                    INSERT INTO features(symbol, ts, feature_name, feature_value)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (symbol, ts, feature_name)
                    DO UPDATE SET feature_value = EXCLUDED.feature_value
                """, (symbol, timestamp, name, float(value)))

    def log_market_price(self, symbol, timestamp, close_price, volume=None):
        if self.offline:
            return

        with self.conn.cursor() as cur:
            cur.execute("""
                        INSERT INTO historical_prices(symbol, ts, close)
                        VALUES (%s, %s, %s) ON CONFLICT DO NOTHING
                        """, (symbol, timestamp, close_price))
    # ------------------------
    # MODEL REGISTRY
    # ------------------------

    def register_model(
        self,
        model_name: str,
        version: str,
        dataset_path: str,
        features: list,
        threshold: float,
        metrics: dict,
    ):
        if self.offline:
            return

        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO model_registry(
                    model_name,
                    version,
                    dataset_path,
                    features,
                    threshold,
                    metrics
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (model_name, version)
                DO UPDATE SET
                    dataset_path = EXCLUDED.dataset_path,
                    features = EXCLUDED.features,
                    threshold = EXCLUDED.threshold,
                    metrics = EXCLUDED.metrics
                """,
                (
                    model_name,
                    version,
                    dataset_path,
                    json.dumps(features),
                    threshold,
                    json.dumps(metrics),
                ),
            )
    # ------------------------
    # INFERENCE LOGGING
    # ------------------------

    def log_inference(
        self,
        model_name: str,
        model_version: str,
        symbol: str,
        timestamp,
        probability: float,
        predicted_label: str,
        features: dict,
    ):
        if self.offline:
            return

        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO inference_log(
                    model_name,
                    model_version,
                    symbol,
                    ts,
                    probability,
                    predicted_label,
                    features
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    model_name,
                    model_version,
                    symbol,
                    timestamp,
                    probability,
                    predicted_label,
                    json.dumps(features),
                ),
            )
    # Комментарии:
    # Возвращает исторические цены (timestamp, close)
    # Нужен для backtest

    def get_historical_prices(self, symbol):

        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT ts, close
                FROM historical_prices
                WHERE symbol = %s
                ORDER BY ts
                """,
                (symbol,)
            )

            rows = cur.fetchall()

        return rows

