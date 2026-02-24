import psycopg2
import numpy as np
from pathlib import Path


def _normalize(value):
    if isinstance(value, np.generic):
        return value.item()
    return value


class PostgresStorage:

    def _signals_id_col(self) -> str:
        """Return the column name used to identify a signal row.

        Current DB schema uses `signal_id` (v1). Older experiments used `event_id`
        or `id`. We detect the best available column at runtime to avoid schema
        drift breaking the runtime.
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public'
                      AND table_name = 'signals'
                      AND column_name IN ('signal_id', 'event_id', 'id')
                    ORDER BY CASE
                        WHEN column_name = 'signal_id' THEN 0
                        WHEN column_name = 'event_id' THEN 1
                        ELSE 2
                    END
                    LIMIT 1
                    """
                )
                row = cur.fetchone()
            # default to the current schema name
            return row[0] if row else 'signal_id'
        except Exception:
            return 'signal_id'

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
        from uuid import uuid4

        # Robust ID resolution across different SignalEvent versions
        signal_id = getattr(event, "signal_id", None) or getattr(event, "event_id", None) or str(uuid4())
        correlation_id = getattr(event, "correlation_id", None) or signal_id
        strategy = getattr(event, "strategy", None) or "sim"
        symbol = getattr(event, "symbol", None)
        signal_type = getattr(event, "signal_type", None)
        strength = getattr(event, "strength", None)
        from datetime import datetime, timezone

        timestamp = getattr(event, "timestamp", None)

        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        elif isinstance(timestamp, (int, float)):
            timestamp = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        if strength is None:
            strength = 1.0

        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO signals (signal_id,
                                     correlation_id,
                                     strategy,
                                     symbol,
                                     signal_type,
                                     strength,
                                     ts,
                                     processed)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (signal_id) DO UPDATE
                SET
                    correlation_id = EXCLUDED.correlation_id,
                    strategy       = EXCLUDED.strategy,
                    symbol         = EXCLUDED.symbol,
                    signal_type    = EXCLUDED.signal_type,
                    strength       = EXCLUDED.strength,
                    ts             = EXCLUDED.ts
                """,
                (
                    signal_id,
                    correlation_id,
                    strategy,
                    symbol,
                    signal_type,
                    float(strength),
                    timestamp,
                    False,
                ),
            )
        # storage/postgres.py (внутри log_signal)
        from datetime import datetime, timezone

        timestamp = getattr(event, "timestamp", None)

        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        elif isinstance(timestamp, (int, float)):
            timestamp = datetime.fromtimestamp(float(timestamp), tz=timezone.utc)
        # если это datetime — оставляем как есть
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
            *,
            symbol: str,
            timestamp=None,
            ts=None,
            timeframe: str = "1m",
            price=None,
            close_price=None,
            open=None,
            high=None,
            low=None,
            volume: float = 0.0,
    ):
        """Persist a bar/price point.

        Normalizes caller kwargs to DB schema:
          market_data(symbol, timeframe, open, high, low, close_price, volume, ts)

        Accepted aliases:
          - `timestamp` or `ts` for bar time
          - `price` as alias for `close_price`
        """
        from datetime import datetime, timezone

        # normalize timestamp
        if ts is None:
            ts = timestamp
        if ts is None:
            ts = datetime.now(timezone.utc)

        # normalize close price
        if close_price is None:
            close_price = price
        if close_price is None:
            raise ValueError("log_market_price: close_price/price is required")

        # best-effort numeric cast (numpy scalars etc.)
        def _f(x):
            if x is None:
                return None
            try:
                return float(x)
            except Exception:
                return x

        o = _f(open)
        h = _f(high)
        l = _f(low)
        c = _f(close_price)
        v = float(volume) if volume is not None else 0.0

        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO market_data (symbol,
                                         timeframe,
                                         open,
                                         high,
                                         low,
                                         close_price,
                                         volume,
                                         ts)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (symbol, timeframe, ts)
                DO
                UPDATE SET
                    open = EXCLUDED.open,
                    high = EXCLUDED.high,
                    low = EXCLUDED.low,
                    close_price = EXCLUDED.close_price,
                    volume = EXCLUDED.volume
                """,
                (symbol, timeframe, o, h, l, c, v, ts),
            )
        self.conn.commit()
    def log_features(self, symbol: str | None = None, features: dict | None = None, timestamp=None, **kwargs):
        """
        Log features for a symbol at a given timestamp.

        Backward/forward compatible:
        - symbol may be passed explicitly
        - or embedded inside an `event`
        - extra kwargs (e.g. event_id) are ignored
        """
        # Resolve symbol
        if symbol is None:
            event = kwargs.get("event")
            if event is not None:
                symbol = getattr(event, "symbol", None)
        if symbol is None:
            # In SIM / backward-compat flows we may receive feature logs
            # without explicit symbol. In that case we skip persistence
            # instead of breaking the pipeline.
            return

        # Resolve features
        if features is None:
            features = kwargs.get("features")
        if not features:
            return

        # Resolve timestamp
        if timestamp is None:
            timestamp = kwargs.get("timestamp") or kwargs.get("ts")
            event = kwargs.get("event")
            if timestamp is None and event is not None:
                timestamp = getattr(event, "timestamp", None)

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

    # ------------------------------------------------------------
    # ------------------- Event Source Stub ----------------------
    # ------------------------------------------------------------

    def get_pending_events(self):
        from market.sim_feed import SimMarketFeed

        feed = SimMarketFeed()
        return feed.generate(steps=30)

    def save_order(self, order):
        """Persist Order.

        v1 stable contract:
          orders(order_id, symbol, side, qty, price, status, signal_event_id, created_ts, updated_ts, filled_qty)

        Hard requirement from DB schema:
          created_ts NOT NULL, updated_ts NOT NULL.

        We defensively coalesce timestamps to avoid NOT NULL violations when upstream
        constructors forget to set `updated_ts`.
        """
        from datetime import datetime, timezone

        from datetime import datetime, timezone

        created_ts = getattr(order, "created_ts", None)
        updated_ts = getattr(order, "updated_ts", None)

        # Normalize timestamps to proper datetime
        if isinstance(created_ts, (int, float)):
            created_ts = datetime.fromtimestamp(created_ts, tz=timezone.utc)

        if isinstance(updated_ts, (int, float)):
            updated_ts = datetime.fromtimestamp(updated_ts, tz=timezone.utc)

        # Coalesce if missing
        if created_ts is None:
            created_ts = datetime.now(timezone.utc)

        if updated_ts is None:
            updated_ts = created_ts

        # Coalesce timestamps to satisfy NOT NULL constraints
        if created_ts is None:
            created_ts = datetime.now(timezone.utc)
        if updated_ts is None:
            updated_ts = created_ts

        # Ensure the referenced signal row exists to satisfy FK (orders.signal_event_id -> signals.signal_id)
        signal_event_id = getattr(order, "signal_event_id", None)
        if signal_event_id:
            sid = self._signals_id_col()
            with self.conn.cursor() as cur:
                cur.execute(f"SELECT 1 FROM signals WHERE {sid} = %s", (signal_event_id,))
                exists = cur.fetchone() is not None
                if not exists:
                    # Minimal stub to preserve referential integrity in SIM/DEV runs
                    cur.execute(
                        f"""
                        INSERT INTO signals ({sid}, correlation_id, strategy, symbol, signal_type, strength, ts, processed)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT ({sid}) DO NOTHING
                        """,
                        (
                            signal_event_id,
                            signal_event_id,
                            "unknown",
                            getattr(order, "symbol", None),
                            getattr(order, "side", None),
                            0.0,
                            created_ts,
                            False,
                        ),
                    )

        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO orders (order_id,
                                    symbol,
                                    side,
                                    qty,
                                    price,
                                    status,
                                    signal_event_id,
                                    created_ts,
                                    updated_ts,
                                    filled_qty)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    getattr(order, "order_id"),
                    getattr(order, "symbol"),
                    getattr(order, "side"),
                    float(getattr(order, "qty")),
                    float(getattr(order, "price")) if getattr(order, "price", None) is not None else None,
                    getattr(order, "status"),
                    getattr(order, "signal_event_id", None),
                    created_ts,
                    updated_ts,
                    float(getattr(order, "filled_qty", 0.0) or 0.0),
                ),
            )

        self.conn.commit()

    def update_order_status(
        self,
        *,
        order_id: str,
        status: str,
        ts,
        filled_qty: float | None = None,
        avg_fill_price: float | None = None,
        **_,
    ):
        """
        Update order status, updated_ts and optionally filled_qty.

        Extra kwargs (e.g. avg_fill_price) are accepted for forward
        compatibility but ignored at storage layer (v1 schema does not
        persist avg_fill_price).
        """
        with self.conn.cursor() as cur:
            if filled_qty is None:
                cur.execute(
                    """
                    UPDATE orders
                    SET status = %s,
                        updated_ts = %s
                    WHERE order_id = %s
                    """,
                    (
                        status,
                        ts,
                        order_id,
                    ),
                )
            else:
                cur.execute(
                    """
                    UPDATE orders
                    SET status = %s,
                        updated_ts = %s,
                        filled_qty = %s
                    WHERE order_id = %s
                    """,
                    (
                        status,
                        ts,
                        float(filled_qty),
                        order_id,
                    ),
                )
        self.conn.commit()

    def save_fill(self, fill):
        """
        Persist FillEvent(fill_id, order_id, symbol, side, qty, price, commission, timestamp).
        """
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO fills (fill_id,
                                   order_id,
                                   symbol,
                                   side,
                                   qty,
                                   price,
                                   commission,
                                   ts)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (fill_id) DO NOTHING
                """,
                (
                    fill.fill_id,
                    fill.order_id,
                    fill.symbol,
                    fill.side,
                    float(fill.qty),
                    float(fill.price),
                    float(fill.commission),
                    fill.timestamp,
                ),
            )
        self.conn.commit()