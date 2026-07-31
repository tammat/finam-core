from datetime import datetime
from zoneinfo import ZoneInfo

from finam_core.strategy.exit_engine import (
    ExitDecision,
    apply_hard_max_hold,
    apply_paper_session_end_exit,
    hard_exit_limit_seconds,
)


def test_hard_exit_converts_hold_without_operator_approval(monkeypatch):
    monkeypatch.setenv("PAPER_HARD_MAX_HOLD_SEC", "3600")
    result = apply_hard_max_hold(
        decision=ExitDecision(False, "hold_long", 99),
        symbol="SBER@MISX", position_age_sec=3601,
    )
    assert result.should_exit
    assert result.reason == "hard_max_hold_exit"


def test_hard_exit_replaces_ordinary_time_exit(monkeypatch):
    monkeypatch.setenv("NG_HARD_MAX_HOLD_SEC", "7200")
    result = apply_hard_max_hold(
        decision=ExitDecision(True, "time_exit", 2.5),
        symbol="NGQ6@RTSX", position_age_sec=7201,
    )
    assert result.reason == "hard_max_hold_exit"


def test_protective_stop_keeps_priority_over_hard_exit(monkeypatch):
    monkeypatch.setenv("BR_HARD_MAX_HOLD_SEC", "3600")
    stop = ExitDecision(True, "stop_loss_long", 90)
    assert apply_hard_max_hold(
        decision=stop, symbol="BRQ6@RTSX", position_age_sec=5000,
    ) == stop


def test_energy_limits_are_separate(monkeypatch):
    monkeypatch.delenv("NG_HARD_MAX_HOLD_SEC", raising=False)
    monkeypatch.delenv("BR_HARD_MAX_HOLD_SEC", raising=False)
    assert hard_exit_limit_seconds("NGQ6@RTSX") == 21600
    assert hard_exit_limit_seconds("BRQ6@RTSX") == 43200


def test_favorable_trend_extends_only_to_absolute_limit(monkeypatch):
    monkeypatch.setenv("METALS_HARD_MAX_HOLD_SEC", "36000")
    extended = apply_hard_max_hold(
        decision=ExitDecision(True, "time_exit", 99), symbol="GDU6@RTSX",
        position_age_sec=36001, favorable_trend_confirmed=True,
    )
    assert not extended.should_exit
    assert extended.reason == "hard_max_hold_trend_extension"
    absolute = apply_hard_max_hold(
        decision=ExitDecision(False, "hold_long", 101), symbol="GDU6@RTSX",
        position_age_sec=72001, favorable_trend_confirmed=True,
    )
    assert absolute.should_exit
    assert absolute.reason == "hard_max_hold_exit"


def test_asset_class_limits_are_explicit(monkeypatch):
    for key in ("USD_HARD_MAX_HOLD_SEC", "METALS_HARD_MAX_HOLD_SEC",
                "INDEX_HARD_MAX_HOLD_SEC", "EQUITY_HARD_MAX_HOLD_SEC"):
        monkeypatch.delenv(key, raising=False)
    assert hard_exit_limit_seconds("USDRUBF@RTSX") == 28800
    assert hard_exit_limit_seconds("GDU6@RTSX") == 36000
    assert hard_exit_limit_seconds("MXU6@RTSX") == 28800
    assert hard_exit_limit_seconds("SBER@MISX") == 28800


def test_paper_session_end_exit_is_last_intraday_safety_barrier():
    hold = ExitDecision(False, "hold_long", 99)
    before = datetime(2026, 7, 29, 23, 39, tzinfo=ZoneInfo("Europe/Moscow"))
    cutoff = datetime(2026, 7, 29, 23, 40, tzinfo=ZoneInfo("Europe/Moscow"))
    assert not apply_paper_session_end_exit(decision=hold, now_msk=before).should_exit
    result = apply_paper_session_end_exit(decision=hold, now_msk=cutoff)
    assert result.should_exit
    assert result.reason == "paper_session_end_exit"


def test_paper_session_end_does_not_override_protective_exit():
    stop = ExitDecision(True, "stop_loss_long", 90)
    now = datetime(2026, 7, 29, 23, 45, tzinfo=ZoneInfo("Europe/Moscow"))
    assert apply_paper_session_end_exit(decision=stop, now_msk=now) == stop
