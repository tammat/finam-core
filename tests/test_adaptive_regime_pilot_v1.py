from decimal import Decimal
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

SOURCE = Path("src/scripts/run_adaptive_regime_pilot_v1.py")
spec = spec_from_file_location("adaptive_pilot", SOURCE)
module = module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(module)


def test_shadow_gate_is_fast_but_cost_aware() -> None:
    metric = module.performance([
        Decimal("1"), Decimal("1"), Decimal("-0.5"), Decimal("1"), Decimal("-0.25")
    ])
    placebo = module.performance([
        Decimal("0.1"), Decimal("-0.1"), Decimal("0"), Decimal("-0.1"), Decimal("0.1")
    ])
    assert module.shadow_decision(metric, placebo, Decimal("1"))[0] == "PILOT_ACTIVE"
    assert module.shadow_decision(metric, placebo, Decimal("0.7"))[0] == "SHADOW_COLLECTING"


def test_pilot_rolls_back_after_two_losses() -> None:
    assert module.paper_decision(
        [Decimal("1"), Decimal("-0.5"), Decimal("-0.6")], Decimal("1")
    ) == ("ROLLED_BACK", "TWO_CONSECUTIVE_PILOT_LOSSES")


def test_pilot_never_enables_real_trading() -> None:
    source = SOURCE.read_text()
    assert 'print("real_trading_allowed=0")' in source
    assert "PILOT_DRAWDOWN_REACHED_TWO_R" in source
    assert "DETERMINISTIC_MEDIAN_RISK_NOT_BEST_PNL" in source
    assert "ADAPTIVE_OR_SKIP" in source
    assert "entry_delay_bars" in source


def test_pipeline_accepts_only_active_adaptive_pilot() -> None:
    source = Path("src/finam_core/pipelines/paper_pipeline.py").read_text()
    assert "adaptive_regime_paper_pilot_v1" in source
    assert "PILOT_ACTIVE" in source
    assert "PAPER_CONFIRMED" in source
    assert "AND p.candidate_code=%s" in source
    assert "AND p.regime_code=%s" in source
    assert "AND symbol=%s" in source
    assert "AND strategy_code=%s" in source
    assert "adaptive_pilot_max_open_positions" in source
    assert "adaptive_pilot_trade_budget_exhausted" in source
    assert "adaptive_pilot_execution_guard_error" in source
    assert 'SELECT count(*) FROM positions WHERE abs(qty)>1e-12' in source
    assert 'intent["qty"] = min(' in source


def test_family_pooling_and_entry_diagnostics_are_wired() -> None:
    controller = SOURCE.read_text()
    builder = Path("src/scripts/analytics/build_entry_exit_optimizer_v1.py").read_text()
    renderer = Path(
        "src/marketcore/presentation/workspace_v2/renderer/"
        "home_compact_v1_domain_renderer.py"
    ).read_text()
    assert "ADAPTIVE_OR_SKIP" in controller
    assert "DETERMINISTIC_MEDIAN_RISK_NOT_BEST_PNL" in controller
    assert "entry_exit_shadow_diagnostic_v1" in builder
    assert "mean_entry_slippage_r" in controller
    assert "adaptive_policy_families" in renderer
