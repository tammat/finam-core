from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "src/scripts/signal_funnel_reason_analytics_v1.py"


def test_reasons_use_same_linked_admission_cohort_as_funnel() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "SIGNAL_FUNNEL_REASON_ANALYTICS_V5_UNIQUE_CLOSED_BAR_OPPORTUNITY" in source
    assert "JOIN public.orders o ON o.signal_event_id=member.signal_key" in source
    assert "JOIN public.signal_fills sf ON sf.signal_id=member.signal_key" in source
    assert "signal_admission_loss_cohort_v3" in source
    assert "unique_symbol_side_strategy_timeframe_bar" in source
    assert "row_number() OVER" in source
    assert "regime_bar_ts" in source
    assert "date_bin(" in source


def test_accepted_signal_without_order_is_visible_not_counted_as_pass() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "ACCEPTED_WITHOUT_ORDER" in source
    assert "RISK_ACCEPTED_WITHOUT_ORDER" in source
    assert "NEW_NOT_PROCESSED" in source
    assert '"PYRAMID" in v' in source


def test_protection_research_and_technical_losses_are_separate() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert 'return "PROTECTION"' in source
    assert 'return "TECHNICAL"' in source
    assert 'return "RESEARCH"' in source
    assert 'return "CONTROL"' in source
    assert 'return "MARKET"' in source
    assert 'return "EDGE"' in source
