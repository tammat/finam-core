from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MarketEventContext:
    has_cbr_event_today: bool
    has_inventory_event_today: bool
    minutes_to_event: int | None
    event_name: str | None
    event_type: str | None
    severity: str | None


class MarketEventCalendarRepository:
    """Русский комментарий: читает календарь рыночных событий из PostgreSQL."""

    def __init__(self, pg_logger: Any) -> None:
        self.pg_logger = pg_logger

    def load_context(self, instrument_group: str) -> MarketEventContext:
        sql = """
        select
            event_type,
            event_name,
            severity,
            round(extract(epoch from (event_time - now())) / 60.0)::int as minutes_to_event
        from market_event_calendar
        where is_active = true
          and instrument_group = %s
          and event_time >= now() - interval '2 hours'
          and event_time <= now() + interval '24 hours'
        order by event_time asc
        limit 1;
        """

        with self.pg_logger._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (instrument_group,))
                row = cur.fetchone()

        if not row:
            return MarketEventContext(
                has_cbr_event_today=False,
                has_inventory_event_today=False,
                minutes_to_event=None,
                event_name=None,
                event_type=None,
                severity=None,
            )

        event_type, event_name, severity, minutes_to_event = row
        event_type = str(event_type)

        return MarketEventContext(
            has_cbr_event_today=event_type == "CBR_RATE_DECISION",
            has_inventory_event_today=event_type in {
                "EIA_INVENTORY",
                "EIA_GAS_STORAGE",
                "API_INVENTORY",
            },
            minutes_to_event=int(minutes_to_event),
            event_name=str(event_name),
            event_type=event_type,
            severity=str(severity),
        )
