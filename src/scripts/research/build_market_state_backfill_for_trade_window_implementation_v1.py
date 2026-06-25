#!/usr/bin/env python3

import os
from datetime import timezone

import psycopg2

from finam_core.research.events import MarketFeaturesReadyEvent
from finam_core.research.event_adapter import ResearchEventAdapter
from finam_core.research.market_state.repository import MarketStateRepository


TARGET_SYMBOL = "BRN6@RTSX"
TARGET_TIMEFRAME = "M5"
WINDOW_START = "2026-05-18T00:00:00+00:00"
WINDOW_END = "2026-05-27T23:59:59+00:00"


def classify_session(ts):
    hour = ts.astimezone(timezone.utc).hour
    if 6 <= hour < 14:
        return "MOSCOW_DAY"
    if 14 <= hour < 21:
        return "MOSCOW_EVENING"
    return "UNKNOWN"


def main() -> int:
    print("=== MARKET_STATE_BACKFILL_FOR_TRADE_WINDOW_IMPLEMENTATION_V1 ===")
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
    repository = MarketStateRepository(db)

    with psycopg2.connect(db) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    symbol,
                    timeframe,
                    ts,
                    close,
                    volatility_state,
                    trend_state,
                    session_state
                FROM public.feature_snapshots
                WHERE symbol=%s
                  AND timeframe=%s
                  AND ts >= %s
                  AND ts <= %s
                ORDER BY ts;
                """,
                (TARGET_SYMBOL, TARGET_TIMEFRAME, WINDOW_START, WINDOW_END),
            )
            rows = cur.fetchall()

    written = 0

    for symbol, timeframe, ts, close, volatility_state, trend_state, session_state in rows:
        trend = str(trend_state or "UNKNOWN").upper()
        volatility = str(volatility_state or "UNKNOWN").upper()
        session = str(session_state or classify_session(ts)).upper()

        event = MarketFeaturesReadyEvent(
            symbol=symbol,
            timeframe=timeframe,
            features={
                "close": float(close),
                "trend": trend,
                "volatility": volatility,
                "session": session,
            },
        )

        state_event = adapter.handle_market_features(event)
        repository.save_market_state_event(
            state_event,
            snapshot_ts=ts,
            asset_class="FUTURES",
            source="market_state_backfill_trade_window_v1",
        )
        written += 1

    print(f"source=public.feature_snapshots")
    print(f"target_symbol={TARGET_SYMBOL}")
    print(f"target_timeframe={TARGET_TIMEFRAME}")
    print(f"rows_loaded={len(rows)}")
    print(f"snapshots_written={written}")
    print("db_update=1")
    print("VERDICT=MARKET_STATE_BACKFILL_FOR_TRADE_WINDOW_IMPLEMENTATION_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
