from __future__ import annotations

import argparse
import psycopg
from datetime import datetime, timezone

from finam_core.analytics.statistics_repository import build_psycopg_url
from finam_core.research.market_event_risk import decide_market_event_risk


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--minutes-before", type=int, default=60)
    parser.add_argument("--minutes-after", type=int, default=30)
    args = parser.parse_args()

    now = datetime.now(timezone.utc)

    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS market_event_calendar (
                    id BIGSERIAL PRIMARY KEY,
                    instrument_group TEXT NOT NULL,
                    event_time TIMESTAMPTZ NOT NULL,
                    event_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    event_name TEXT NOT NULL,
                    source TEXT NOT NULL DEFAULT 'manual',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                );
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS strategy_event_risk_context (
                    id BIGSERIAL PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    strategy TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    trade_source TEXT NOT NULL,
                    event_status TEXT NOT NULL,
                    allow_runtime BOOLEAN NOT NULL,
                    risk_multiplier NUMERIC NOT NULL,
                    nearest_event_ts TIMESTAMPTZ,
                    nearest_event_type TEXT,
                    nearest_event_impact TEXT,
                    reason TEXT NOT NULL,
                    calculated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    UNIQUE(symbol, strategy, timeframe, trade_source)
                );
            """)

            cur.execute("""
                SELECT DISTINCT symbol, strategy, timeframe, trade_source
                FROM strategy_statistics_v2
                ORDER BY symbol, strategy, timeframe
            """)

            rows = cur.fetchall()
            saved = 0

            for symbol, strategy, timeframe, trade_source in rows:
                root = str(symbol).split("@")[0]
                if root.startswith("BR"):
                    root = "BR"
                elif root.startswith("NG"):
                    root = "NG"
                elif root.startswith("USD") or root.startswith("Si"):
                    root = "USD"
                elif root.startswith("SBER"):
                    root = "SBER"
                elif root.startswith("PLZL"):
                    root = "PLZL"

                cur.execute("""
                    SELECT event_time, event_type, severity
                    FROM market_event_calendar
                    WHERE instrument_group IN (%s, 'ALL')
                      AND event_time >= now() - (%s || ' minutes')::interval
                      AND event_time <= now() + (%s || ' minutes')::interval
                    ORDER BY
                      CASE impact
                        WHEN 'CRITICAL' THEN 1
                        WHEN 'HIGH' THEN 2
                        WHEN 'MEDIUM' THEN 3
                        ELSE 4
                      END,
                      abs(extract(epoch from (event_time - now())))
                    LIMIT 1
                """, (root, args.minutes_after, args.minutes_before))

                ev = cur.fetchone()

                if ev:
                    event_ts, event_type, impact = ev
                else:
                    event_ts, event_type, impact = None, None, None

                decision = decide_market_event_risk(
                    now=now,
                    nearest_event_ts=event_ts,
                    impact=impact,
                    minutes_before=args.minutes_before,
                    minutes_after=args.minutes_after,
                )

                cur.execute("""
                    INSERT INTO strategy_event_risk_context (
                        symbol, strategy, timeframe, trade_source,
                        event_status, allow_runtime, risk_multiplier,
                        nearest_event_ts, nearest_event_type, nearest_event_impact,
                        reason, calculated_at
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now())
                    ON CONFLICT (symbol, strategy, timeframe, trade_source)
                    DO UPDATE SET
                        event_status=EXCLUDED.event_status,
                        allow_runtime=EXCLUDED.allow_runtime,
                        risk_multiplier=EXCLUDED.risk_multiplier,
                        nearest_event_ts=EXCLUDED.nearest_event_ts,
                        nearest_event_type=EXCLUDED.nearest_event_type,
                        nearest_event_impact=EXCLUDED.nearest_event_impact,
                        reason=EXCLUDED.reason,
                        calculated_at=now()
                """, (
                    symbol, strategy, timeframe, trade_source,
                    decision.status, decision.allow_runtime, decision.risk_multiplier,
                    event_ts, event_type, impact,
                    decision.reason,
                ))

                print(
                    "STRATEGY_EVENT_RISK "
                    f"symbol={symbol} strategy={strategy} timeframe={timeframe} "
                    f"status={decision.status} runtime={decision.allow_runtime} "
                    f"risk_multiplier={decision.risk_multiplier} reason={decision.reason}",
                    flush=True,
                )

                saved += 1

        conn.commit()

    print(f"STRATEGY_EVENT_RISK_CONTEXT_SUMMARY total={saved}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
