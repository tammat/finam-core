#!/usr/bin/env python3

import os
from datetime import timezone

import psycopg2

from finam_core.research.events import MarketFeaturesReadyEvent
from finam_core.research.event_adapter import ResearchEventAdapter


SOURCE = "market_index_context_backfill_v1"

CONTEXTS = [
    ("FX_USDRUB", "%USD%"),
    ("ENERGY_BR", "%BR%"),
]


def main() -> int:

    print("=== MARKET_INDEX_CONTEXT_BACKFILL_V1 ===")
    print("mode=backfill_apply")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("real_trading_enabled=0")
    print("orders_sent=0")

    db = os.environ.get("DATABASE_URL", "")

    if not db:
        print("db_update=0")
        print("ERROR=DATABASE_URL_NOT_SET")
        return 2

    if db.startswith("sqlite"):
        print("db_update=0")
        print("ERROR=SQLITE_FORBIDDEN")
        return 2

    adapter = ResearchEventAdapter()

    written = 0

    with psycopg2.connect(db) as conn:
        with conn.cursor() as cur:

            for context_code, pattern in CONTEXTS:

                cur.execute(
                    """
                    SELECT
                        symbol,
                        timeframe,
                        ts,
                        close,
                        trend_state,
                        volatility_state,
                        session_state
                    FROM public.feature_snapshots
                    WHERE symbol ILIKE %s
                    ORDER BY ts;
                    """,
                    (pattern,),
                )

                rows = cur.fetchall()

                for (
                    symbol,
                    timeframe,
                    ts,
                    close,
                    trend_state,
                    volatility_state,
                    session_state,
                ) in rows:

                    event = MarketFeaturesReadyEvent(
                        symbol=symbol,
                        timeframe=timeframe,
                        features={
                            "close": float(close),
                            "trend": str(trend_state or "UNKNOWN").upper(),
                            "volatility": str(volatility_state or "UNKNOWN").upper(),
                            "session": str(session_state or "UNKNOWN").upper(),
                        },
                    )

                    state = adapter.handle_market_features(event)

                    cur.execute(
                        """
                        INSERT INTO research.market_index_state_context_v1
                        (
                            context_ts,
                            context_code,
                            context_symbol,
                            timeframe,
                            trend_state,
                            volatility_state,
                            session_state,
                            close,
                            canonical_context_signature,
                            compact_context_signature,
                            source
                        )
                        VALUES
                        (
                            %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
                        )
                        ON CONFLICT
                        (
                            context_ts,
                            context_code,
                            context_symbol,
                            timeframe,
                            compact_context_signature
                        )
                        DO NOTHING;
                        """,
                        (
                            ts,
                            context_code,
                            symbol,
                            timeframe,
                            trend_state,
                            volatility_state,
                            session_state,
                            close,
                            state.canonical_signature,
                            state.compact_signature,
                            SOURCE,
                        ),
                    )

                    written += cur.rowcount

        conn.commit()

    print(f"contexts_written={written}")
    print("db_update=1")
    print("VERDICT=MARKET_INDEX_CONTEXT_BACKFILL_OK")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
