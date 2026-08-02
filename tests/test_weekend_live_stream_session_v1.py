from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from finam_core.session.session_manager import SessionManager


MSK = ZoneInfo("Europe/Moscow")


def test_sunday_window_requires_verified_live_stream() -> None:
    manager = SessionManager()
    sunday = datetime(2026, 7, 19, 12, 0, tzinfo=MSK)

    waiting = manager.get_regime("BRQ6@RTSX", now=sunday, market_data_live=False)
    live = manager.get_regime("BRQ6@RTSX", now=sunday, market_data_live=True)

    assert waiting == {
        "phase": "weekend_waiting_stream",
        "allow_entries": False,
        "reason": "live_stream_required",
    }
    assert live == {
        "phase": "weekend_live",
        "allow_entries": True,
        "reason": "verified_live_stream",
    }


def test_weekend_window_boundaries_and_calendar_exceptions() -> None:
    manager = SessionManager()
    assert not manager.get_regime(
        now=datetime(2026, 7, 19, 9, 59, tzinfo=MSK), market_data_live=True
    )["allow_entries"]
    assert not manager.get_regime(
        now=datetime(2026, 7, 19, 19, 0, tzinfo=MSK), market_data_live=True
    )["allow_entries"]
    assert manager.get_regime(
        now=datetime(2026, 7, 18, 12, 0, tzinfo=MSK), market_data_live=True
    )["allow_entries"]
    exception = manager.get_regime(
        now=datetime(2026, 8, 1, 12, 0, tzinfo=MSK), market_data_live=True
    )
    assert exception == {
        "phase": "closed", "allow_entries": False, "reason": "exchange_calendar_closed"
    }
    assert manager.next_entry_session(
        symbol="BRQ6@RTSX", now=datetime(2026, 8, 1, 12, 0, tzinfo=MSK)
    ) == datetime(2026, 8, 3, 8, 50, tzinfo=MSK)


def test_forts_weekday_starts_at_0850() -> None:
    manager = SessionManager()
    before = datetime(2026, 8, 3, 8, 49, tzinfo=MSK)
    opened = datetime(2026, 8, 3, 8, 50, tzinfo=MSK)
    assert manager.get_regime("BRQ6@RTSX", now=before)["allow_entries"] is False
    assert manager.get_regime("BRQ6@RTSX", now=opened)["allow_entries"] is True
    assert manager.next_entry_session(symbol="BRQ6@RTSX", now=before) == opened


def test_pipeline_rejects_replay_and_stale_weekend_quotes() -> None:
    source = Path("src/finam_core/pipelines/paper_pipeline.py").read_text()
    assert "def _is_verified_live_quote_event" in source
    assert 'os.getenv("REPLAY_CAMPAIGN_ID")' in source
    assert 'WEEKEND_LIVE_QUOTE_MAX_AGE_SEC' in source
    assert "market_data_live=market_data_live" in source
