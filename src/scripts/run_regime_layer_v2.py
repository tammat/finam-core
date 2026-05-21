from __future__ import annotations

import os
import psycopg2

from finam_core.alpha.regime_layer_v2 import RegimeLayerV2


def ensure_regime_table(cur) -> None:
    cur.execute("""
        create table if not exists regime_state (
            symbol text primary key,
            trend text not null,
            volatility text not null,
            regime text not null,
            tradable boolean not null,
            confidence numeric not null,
            reason text,
            updated_at timestamptz not null default now()
        )
    """)


def load_prices(conn, symbol: str, limit: int) -> list[float]:
    try:
        with conn.cursor() as cur:
            cur.execute("""
                select close
                from market_bars
                where symbol=%s
                order by ts desc
                limit %s
            """, (symbol, limit))

            rows = cur.fetchall()
            return [float(r[0]) for r in reversed(rows)]

    except psycopg2.errors.UndefinedTable:
        conn.rollback()

        with conn.cursor() as cur:
            cur.execute("""
                select current_price
                from real_portfolio_positions
                where symbol=%s
                  and coalesce(current_price,0) > 0
                limit 1
            """, (symbol,))

            row = cur.fetchone()
            if not row:
                return []

            return [float(row[0])] * 30


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is empty")

    symbol = os.getenv("REGIME_SYMBOL", "SBER@MISX").strip().upper()
    limit = int(os.getenv("REGIME_PRICE_LIMIT", "120"))

    conn = psycopg2.connect(dsn)

    try:
        prices = load_prices(conn, symbol, limit)

        decision = RegimeLayerV2().classify(
            symbol=symbol,
            prices=prices,
        )

        with conn:
            with conn.cursor() as cur:
                ensure_regime_table(cur)

                cur.execute("""
                    insert into regime_state (
                        symbol, trend, volatility, regime,
                        tradable, confidence, reason, updated_at
                    )
                    values (%s,%s,%s,%s,%s,%s,%s,now())
                    on conflict (symbol) do update
                    set
                        trend=excluded.trend,
                        volatility=excluded.volatility,
                        regime=excluded.regime,
                        tradable=excluded.tradable,
                        confidence=excluded.confidence,
                        reason=excluded.reason,
                        updated_at=now()
                """, (
                    decision.symbol,
                    decision.trend,
                    decision.volatility,
                    decision.regime,
                    decision.tradable,
                    decision.confidence,
                    decision.reason,
                ))

        print(
            f"REGIME_LAYER_V2_STATE symbol={decision.symbol} "
            f"trend={decision.trend} volatility={decision.volatility} "
            f"regime={decision.regime} tradable={decision.tradable} "
            f"confidence={decision.confidence} reason={decision.reason}",
            flush=True,
        )

        print("REGIME_LAYER_V2_OK")
        return 0

    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
