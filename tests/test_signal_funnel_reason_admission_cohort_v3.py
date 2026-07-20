from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "src/scripts/signal_funnel_reason_analytics_v1.py"


def test_reasons_use_same_linked_admission_cohort_as_funnel() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "SIGNAL_FUNNEL_REASON_ANALYTICS_V3_ADMISSION_COHORT" in source
    assert "NOT EXISTS (SELECT 1 FROM public.orders" in source
    assert "NOT EXISTS (SELECT 1 FROM public.signal_fills" in source
    assert "signal_admission_loss_cohort_v3" in source
    assert "distinct_origin_signal" in source


def test_accepted_signal_without_order_is_visible_not_counted_as_pass() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "ACCEPTED_WITHOUT_ORDER" in source
    assert "RISK_ACCEPTED_WITHOUT_ORDER" in source
    assert "NEW_NOT_PROCESSED" in source
    assert '"PYRAMID" in v' in source
