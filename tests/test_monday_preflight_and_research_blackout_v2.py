import importlib.util
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
MSK = ZoneInfo("Europe/Moscow")
SPEC = importlib.util.spec_from_file_location(
    "research_queue", ROOT / "src/scripts/run_market_universe_research_queue_cycle_v1.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


def test_weekday_market_open_blackout() -> None:
    allowed, reason = MODULE.admission_decision(datetime(2026, 8, 3, 6, 50, tzinfo=MSK))
    assert not allowed
    assert reason == "MARKET_OPEN_BLACKOUT_0640_0720_MSK"


def test_preflight_is_timeframe_aware() -> None:
    source = (ROOT / "src/scripts/check_monday_preflight_v2.py").read_text()
    assert 'return ("M1",)' in source
    assert 'return ("M1", "M5")' in source
    assert 'return ("M1", "M5", "M15")' in source
    assert "ORPHAN_LIFECYCLE" in source
    assert "ACTIVE_CONTRACT_MISSING" in source
    assert "V5_OBSERVATION_SOURCE_MISSING" in source
    for symbol in ("BRQ6@RTSX", "SBER@MISX", "GDU6@RTSX", "CNYRUBF@RTSX"):
        assert symbol in source


def test_timer_has_three_open_checkpoints() -> None:
    timer = (ROOT / "deploy/systemd/finam-monday-preflight-v2.timer").read_text()
    assert "06:45:00" in timer
    assert "06:56:00" in timer
    assert "07:06:00" in timer


def test_orphan_cleanup_is_quarantined_and_recoverable() -> None:
    source = (ROOT / "src/scripts/quarantine_orphan_lifecycle_v1.py").read_text()
    assert "orphan_lifecycle_quarantine_v1" in source
    assert "previous_remaining_qty" in source
    assert "LEFT JOIN real_portfolio_positions" in source
    assert "SET remaining_qty=0" in source
