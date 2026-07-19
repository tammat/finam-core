from datetime import datetime
from zoneinfo import ZoneInfo

from scripts.run_market_pipeline import _session_bounds


MSK = ZoneInfo("Europe/Moscow")


def test_sunday_session_is_10_to_19_msk():
    bounds = _session_bounds(datetime(2026, 7, 19, 12, tzinfo=MSK))
    assert bounds is not None
    assert bounds[0].hour == 10
    assert bounds[1].hour == 19


def test_saturday_has_no_session():
    assert _session_bounds(datetime(2026, 7, 18, 12, tzinfo=MSK)) is None


def test_weekday_session_has_bounded_close():
    bounds = _session_bounds(datetime(2026, 7, 20, 12, tzinfo=MSK))
    assert bounds is not None
    assert (bounds[0].hour, bounds[1].hour, bounds[1].minute) == (7, 23, 50)
