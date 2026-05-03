from datetime import datetime, timezone
from finam_core.data.mtf_aggregator import MTFBarAggregator

agg = MTFBarAggregator(("M1", "M5", "M15"))

events = [
    ("NGH6@RTSX", 100.0, 1, datetime(2026, 5, 1, 10, 0, 10, tzinfo=timezone.utc)),
    ("NGH6@RTSX", 101.0, 2, datetime(2026, 5, 1, 10, 0, 50, tzinfo=timezone.utc)),
    ("NGH6@RTSX", 102.0, 1, datetime(2026, 5, 1, 10, 1, 1, tzinfo=timezone.utc)),
]

closed = []
for e in events:
    closed.extend(agg.update(*e))

assert len(closed) == 1
assert closed[0].timeframe == "M1"
assert closed[0].open == 100.0
assert closed[0].high == 101.0
assert closed[0].low == 100.0
assert closed[0].close_price == 101.0
assert closed[0].volume == 3

print("OK: MTF aggregator works")
