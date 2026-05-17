create unique index if not exists ux_market_event_calendar_event_key
on market_event_calendar (
    event_time,
    event_type,
    instrument_group,
    event_name
);
