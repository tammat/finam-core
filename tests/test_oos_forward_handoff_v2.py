from pathlib import Path


def test_handoff_is_deterministic_and_does_not_touch_incubator() -> None:
    source=Path("src/scripts/build_profit_funnel_oos_forward_handoff_v2.py").read_text()
    assert "uuid.uuid5" in source
    assert "OOS_PASS" in source and "promotion_allowed=true" in source
    assert "INSERT INTO analytics.profit_funnel_oos_forward_handoff_v2" in source
    assert "INSERT INTO analytics.forward_edge_incubator_v1" not in source


def test_handoff_cannot_enable_runtime_or_live() -> None:
    migration=Path("sql/analytics/055_profit_funnel_oos_forward_handoff_v2.sql").read_text()
    assert "CHECK (NOT runtime_allowed AND NOT live_allowed)" in migration
    assert "AWAITING_FORWARD_ADMISSION" not in migration
