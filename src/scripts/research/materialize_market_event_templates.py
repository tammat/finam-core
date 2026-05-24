from __future__ import annotations

import psycopg
from datetime import datetime, timedelta, timezone

from finam_core.analytics.statistics_repository import build_psycopg_url


def main() -> int:
    now = datetime.now(timezone.utc)
    horizon = now + timedelta(days=14)

    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS market_event_templates (
                    id BIGSERIAL PRIMARY KEY,
                    instrument_group TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    event_name TEXT NOT NULL,
                    severity TEXT NOT NULL DEFAULT 'HIGH',
                    weekday INTEGER NOT NULL,
                    hour_utc INTEGER NOT NULL,
                    minute_utc INTEGER NOT NULL DEFAULT 0,
                    pre_event_block_min INTEGER NOT NULL DEFAULT 30,
                    pre_event_reduce_min INTEGER NOT NULL DEFAULT 90,
                    source TEXT NOT NULL DEFAULT 'template',
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    UNIQUE(instrument_group, event_type, weekday, hour_utc, minute_utc)
                );
            """)

            cur.execute("""
                SELECT instrument_group, event_type, event_name, severity,
                       weekday, hour_utc, minute_utc,
                       pre_event_block_min, pre_event_reduce_min, source
                FROM market_event_templates
                WHERE is_active = TRUE
            """)

            templates = cur.fetchall()
            inserted = 0

            for tpl in templates:
                group, event_type, event_name, severity, weekday, hour, minute, block_min, reduce_min, source = tpl

                d = now.date()
                while datetime.combine(d, datetime.min.time(), tzinfo=timezone.utc) <= horizon:
                    candidate = datetime(d.year, d.month, d.day, int(hour), int(minute), tzinfo=timezone.utc)

                    if candidate.weekday() == int(weekday) and candidate >= now:
                        cur.execute("""
                            INSERT INTO market_event_calendar (
                                event_time,
                                event_type,
                                instrument_group,
                                event_name,
                                severity,
                                source,
                                pre_event_block_min,
                                pre_event_reduce_min,
                                is_active,
                                raw_json
                            )
                            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,true,'{}'::jsonb)
                            ON CONFLICT (event_time, event_type, instrument_group, event_name)
                            DO NOTHING
                        """, (
                            candidate,
                            event_type,
                            group,
                            event_name,
                            severity,
                            source,
                            block_min,
                            reduce_min,
                        ))
                        inserted += cur.rowcount or 0

                    d += timedelta(days=1)

        conn.commit()

    print(f"MARKET_EVENT_TEMPLATES_MATERIALIZED inserted={inserted}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
