from datetime import datetime
from zoneinfo import ZoneInfo

from scripts.backfill_forward_edge_context_v1 import session_code


UTC = ZoneInfo("UTC")


def test_session_code_uses_moscow_trading_periods() -> None:
    assert session_code(datetime(2026, 7, 15, 4, 0, tzinfo=UTC)) == "PREMARKET"
    assert session_code(datetime(2026, 7, 15, 7, 0, tzinfo=UTC)) == "MORNING"
    assert session_code(datetime(2026, 7, 15, 11, 0, tzinfo=UTC)) == "DAY"
    assert session_code(datetime(2026, 7, 15, 16, 0, tzinfo=UTC)) == "EVENING"
    assert session_code(datetime(2026, 7, 15, 1, 0, tzinfo=UTC)) == "OVERNIGHT"


def test_backfill_is_causal_and_uses_baseline_cohort() -> None:
    source = __import__("inspect").getsource(__import__("scripts.backfill_forward_edge_context_v1", fromlist=["main"]))
    assert "forward_edge_baseline_cohort_id_v1" in source
    assert "s.ts <= o.signal_ts" in source
    assert "s.ts >= o.signal_ts - interval '15 minutes'" in source
