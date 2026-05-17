delete from market_event_calendar a
using market_event_calendar b
where a.id > b.id
  and a.event_time = b.event_time
  and a.event_type = b.event_type
  and a.instrument_group = b.instrument_group
  and a.event_name = b.event_name;
