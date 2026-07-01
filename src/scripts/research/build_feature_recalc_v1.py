from __future__ import annotations

import os
from decimal import Decimal

import psycopg2


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")


def ensure_schema() -> None:
    with psycopg2.connect(DB) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS analytics_global_edge_features_v2 (
                    id BIGSERIAL PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    symbol TEXT NOT NULL,
                    asset_class TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    bars_count BIGINT NOT NULL DEFAULT 0,
                    last_close NUMERIC,
                    atr_proxy NUMERIC,
                    return_proxy NUMERIC,
                    status TEXT NOT NULL,
                    UNIQUE(symbol, timeframe)
                );
                """
            )


def _table_exists(cur: object, name: str) -> bool:
    cur.execute("SELECT to_regclass(%s)", (name,))
    return cur.fetchone()[0] is not None


def recalc_features() -> int:
    ensure_schema()

    with psycopg2.connect(DB) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT symbol, asset_class
                FROM analytics_global_edge_universe_v2
                WHERE status='READY'
                ORDER BY symbol;
                """
            )
            universe = cur.fetchall()

            saved = 0

            for symbol, asset_class in universe:
                timeframe = "M5"
                bars_count = 0
                last_close = None
                atr_proxy = None
                return_proxy = None
                status = "NO_BARS"

                if _table_exists(cur, "public.market_bars"):
                    cur.execute(
                        """
                        SELECT
                            count(*),
                            max(close),
                            max(high) - min(low),
                            max(close) - min(close)
                        FROM public.market_bars
                        WHERE symbol = %s
                           OR symbol = split_part(%s, '@', 1);
                        """,
                        (symbol, symbol),
                    )
                    row = cur.fetchone()
                    bars_count = int(row[0] or 0)
                    last_close = row[1]
                    atr_proxy = row[2]
                    return_proxy = row[3]
                    status = "READY" if bars_count > 0 else "NO_BARS"

                cur.execute(
                    """
                    INSERT INTO analytics_global_edge_features_v2
                        (symbol, asset_class, timeframe, bars_count, last_close, atr_proxy, return_proxy, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (symbol, timeframe)
                    DO UPDATE SET
                        created_at = now(),
                        asset_class = EXCLUDED.asset_class,
                        bars_count = EXCLUDED.bars_count,
                        last_close = EXCLUDED.last_close,
                        atr_proxy = EXCLUDED.atr_proxy,
                        return_proxy = EXCLUDED.return_proxy,
                        status = EXCLUDED.status;
                    """,
                    (
                        symbol,
                        asset_class,
                        timeframe,
                        bars_count,
                        last_close,
                        atr_proxy,
                        return_proxy,
                        status,
                    ),
                )
                saved += 1

            return saved


def main() -> None:
    saved = recalc_features()

    print("=== FEATURE_RECALC_V1 ===")
    print("mode=research_only")
    print(f"features_saved={saved}")
    print("timeframe=M5")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("next=MASS_REPLAY_V2")
    print("VERDICT=FEATURE_RECALC_V1_READY")


if __name__ == "__main__":
    main()
