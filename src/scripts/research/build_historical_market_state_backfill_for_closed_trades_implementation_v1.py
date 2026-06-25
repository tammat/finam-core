#!/usr/bin/env python3

import os
from datetime import timezone

import psycopg2

from finam_core.research.events import MarketFeaturesReadyEvent
from finam_core.research.event_adapter import ResearchEventAdapter
from finam_core.research.market_state.repository import MarketStateRepository


SOURCE = "market_state_backfill_closed_trades_v1"


def main() -> int:
    print("=== HISTORICAL_MARKET_STATE_BACKFILL_FOR_CLOSED_TRADES_IMPLEMENTATION_V1 ===")
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
            cur.execute("""
                WITH full_windows AS (
                    SELECT
                        ct.symbol,
                        ct.timeframe,
                        MIN(ct.entry_ts) AS first_entry,
                        MAX(ct.entry_ts) AS last_entry
                    FROM public.closed_trades ct
                    JOIN (
                        SELECT
                            symbol,
                            timeframe,
                            COUNT(*) AS feature_rows,
                            MIN(ts) AS first_feature,
                            MAX(ts) AS last_feature
                        FROM public.feature_snapshots
                        GROUP BY symbol, timeframe
                    ) fs
                      ON fs.symbol = ct.symbol
                     AND fs.timeframe = ct.timeframe
                    WHERE ct.symbol IS NOT NULL
                      AND ct.timeframe IS NOT NULL
                      AND ct.entry_ts IS NOT NULL
                    GROUP BY ct.symbol, ct.timeframe, fs.first_feature, fs.last_feature
                    HAVING fs.first_feature <= MIN(ct.entry_ts)
                       AND fs.last_feature >= MAX(ct.entry_ts)
                )
                SELECT
                    fs.symbol,
                    fs.timeframe,
                    fs.ts,
                    fs.close,
                    fs.volatility_state,
                    fs.trend_state,
                    fs.session_state
                FROM public.feature_snapshots fs
                JOIN full_windows w
                  ON w.symbol = fs.symbol
                 AND w.timeframe = fs.timeframe
                WHERE fs.ts >= w.first_entry
                  AND fs.ts <= w.last_entry
                ORDER BY fs.symbol, fs.timeframe, fs.ts;
            """)
            rows = cur.fetchall()

    written = 0

    for symbol, timeframe, ts, close, volatility_state, trend_state, session_state in rows:
        if close is None:
            continue

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

        state_event = adapter.handle_market_features(event)
        repository.save_market_state_event(
            state_event,
            snapshot_ts=ts,
            asset_class="FUTURES",
            source=SOURCE,
        )
        written += 1

    print(f"source=public.feature_snapshots")
    print(f"target_source={SOURCE}")
    print(f"feature_rows_loaded={len(rows)}")
    print(f"snapshots_written={written}")
    print("db_update=1")
    print("VERDICT=HISTORICAL_MARKET_STATE_BACKFILL_FOR_CLOSED_TRADES_IMPLEMENTATION_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
