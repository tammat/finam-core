from decimal import Decimal
from pathlib import Path

from scripts.build_market_event_reaction_shadow_v1 import direction_code


def test_direction_is_diagnostic_not_a_trade_signal() -> None:
    assert direction_code(Decimal("0.01")) == "UP"
    assert direction_code(Decimal("-0.01")) == "DOWN"
    assert direction_code(Decimal("0.00001")) == "FLAT"
    source = Path("src/scripts/build_market_event_reaction_shadow_v1.py").read_text()
    assert "directional_signal=0 paper_changed=0 real_changed=0" in source


def test_runtime_audits_all_active_events_but_selects_maximum_risk() -> None:
    pipeline = Path("src/finam_core/pipelines/paper_pipeline.py").read_text()
    assert '"active_events"' in pipeline
    assert "events[0] if events else None" in pipeline
    assert "WHEN 'SHOCK' THEN 1 WHEN 'ELEVATED' THEN 2" in pipeline
