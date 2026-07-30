from finam_core.strategy.exit_engine import ExitDecision, apply_hard_max_hold, hard_exit_limit_seconds


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
