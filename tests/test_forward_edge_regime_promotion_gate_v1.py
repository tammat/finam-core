from decimal import Decimal
import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "src" / "scripts" / "build_forward_edge_regime_promotion_gate_v1.py"
SPEC = importlib.util.spec_from_file_location("promotion_gate", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
POLICY = {
    "minimum_closed_observations": 30, "minimum_calendar_days": 90,
    "minimum_attribution_coverage": 0.95, "minimum_tested_regimes": 2,
    "minimum_positive_regime_share": 0.6, "minimum_total_net_pnl": 0,
    "require_positive_regime_net_pnl": True, "require_nonnegative_regime_delta": True,
}


def test_gate_passes_only_complete_regime_stable_evidence() -> None:
    summary = {
        "closed": 40, "calendar_days": 100, "coverage": Decimal("1"),
        "tested_regimes": 3, "positive_share": Decimal("0.6667"), "variant_net": Decimal("12"),
        "nonpositive_regimes": [], "negative_delta_regimes": [],
    }
    assert MODULE.evaluate(summary, POLICY) == (True, [])


def test_gate_fails_closed_on_negative_regime_delta() -> None:
    summary = {
        "closed": 40, "calendar_days": 100, "coverage": Decimal("1"),
        "tested_regimes": 3, "positive_share": Decimal("1"), "variant_net": Decimal("12"),
        "nonpositive_regimes": [], "negative_delta_regimes": ["compression"],
    }
    allowed, reasons = MODULE.evaluate(summary, POLICY)
    assert allowed is False
    assert reasons == ["NEGATIVE_DELTA_ELIGIBLE_REGIME"]


def test_gate_fails_closed_without_observations() -> None:
    summary = {
        "closed": 0, "calendar_days": 0, "coverage": Decimal("0"),
        "tested_regimes": 0, "positive_share": Decimal("0"), "variant_net": Decimal("0"),
        "nonpositive_regimes": [], "negative_delta_regimes": [],
    }
    allowed, reasons = MODULE.evaluate(summary, POLICY)
    assert allowed is False
    assert "INSUFFICIENT_CLOSED_OBSERVATIONS" in reasons
    assert "INSUFFICIENT_REGIME_COVERAGE" in reasons
