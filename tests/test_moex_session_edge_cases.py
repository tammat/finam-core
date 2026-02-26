from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import random

from domain.session.moex import MoexSession

TZ = ZoneInfo("Europe/Moscow")


def _assert_open_10(dt: datetime, y: int, m: int, d: int):
    assert dt.year == y
    assert dt.month == m
    assert dt.day == d
    assert dt.hour == 10
    assert dt.minute == 0


def test_next_open_boundaries_parametrized():
    session = MoexSession()

    cases = [
        (datetime(2024, 12, 31, 23, 59, tzinfo=TZ), (2025, 1, 1)),
        (datetime(2025, 2, 28, 23, 59, tzinfo=TZ), (2025, 3, 1)),
        (datetime(2024, 2, 29, 23, 59, tzinfo=TZ), (2024, 3, 1)),
    ]

    for now, (y, m, d) in cases:
        nxt = session.next_open(now)
        _assert_open_10(nxt, y, m, d)


def test_weekend_open_before_session():
    session = MoexSession()
    now = datetime(2025, 3, 1, 9, 0, tzinfo=TZ)  # Sat 09:00
    nxt = session.next_open(now)
    _assert_open_10(nxt, 2025, 3, 1)


def test_weekend_open_after_close():
    session = MoexSession()
    now = datetime(2025, 3, 1, 20, 0, tzinfo=TZ)  # Sat 20:00
    nxt = session.next_open(now)
    _assert_open_10(nxt, 2025, 3, 2)


def test_next_open_fuzz_dates_safe_across_calendar():
    """
    Property-style test (deterministic random):
      - next_open must be tz-aware
      - next_open >= now
      - if market is closed -> next_open is at 10:00
    """
    session = MoexSession()
    rng = random.Random(1337)

    start = datetime(2020, 1, 1, 0, 0, tzinfo=TZ)
    end = datetime(2030, 12, 31, 23, 59, tzinfo=TZ)
    total_minutes = int((end - start).total_seconds() // 60)

    for _ in range(2000):
        now = start + timedelta(minutes=rng.randint(0, total_minutes))
        nxt = session.next_open(now)

        assert nxt.tzinfo is not None
        assert nxt >= now

        if not session.is_open(now):
            assert nxt.hour == 10
            assert nxt.minute == 0