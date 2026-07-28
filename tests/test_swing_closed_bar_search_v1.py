from datetime import datetime
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = Path(__file__).resolve().parents[1]
spec = spec_from_file_location("swing_gate", ROOT / "src/scripts/run_swing_closed_bar_search_v1.py")
module = module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


def test_bar_gate_requires_a_new_closed_bar() -> None:
    previous = {"H1": "2026-07-25T18:00:00+03:00", "H4": "2026-07-25T16:00:00+03:00", "D1": "2026-07-25T00:00:00+03:00"}
    assert not module.bars_advanced(previous, dict(previous))
    current = dict(previous)
    current["H1"] = "2026-07-27T07:00:00+03:00"
    assert module.bars_advanced(previous, current)
    assert not module.bars_advanced(previous, {**previous, "H1": "2026-07-25T18:00:00+03"})


def test_market_hours_keep_swing_on_one_cpu_window() -> None:
    assert module.market_hours(datetime(2026, 7, 27, 10, 0, tzinfo=ZoneInfo("Europe/Moscow")))
    assert not module.market_hours(datetime(2026, 7, 27, 2, 0, tzinfo=ZoneInfo("Europe/Moscow")))


def test_db_scheduler_uses_closed_bar_executor() -> None:
    scheduler = (ROOT / "src/scripts/run_db_job_scheduler_v1.py").read_text()
    migration = (ROOT / "sql/analytics/212_swing_closed_bar_schedule_gate_v1.sql").read_text()
    assert "SWING_CLOSED_BAR_SEARCH_V1" in scheduler
    assert "SWING_EDGE_SEARCH_NIGHT" in migration and "SWING_EDGE_SEARCH_WEEKEND" in migration
    assert "WAITING_NEW_BAR" in migration
