from pathlib import Path

from scripts.audit_pnl_units_v1 import asset_class
from scripts.govern_research_experiments_v1 import parameter_hash


ROOT = Path(__file__).resolve().parents[1]


def test_asset_classes_cover_equities_and_futures() -> None:
    assert asset_class("SBER@MISX") == "EQUITY"
    assert asset_class("BRQ6@RTSX") == "FUTURES"


def test_global_fingerprint_excludes_execution_only_fields() -> None:
    base = {"lookback": 40, "hold": 20, "threshold": 1.5}
    assert parameter_hash(base) == parameter_hash({**base, "commission": 10, "slippage": 2})


def test_cycle_contains_governance_before_methodology() -> None:
    runner = (ROOT / "src/scripts/run_autonomous_edge_search_cycle_v1.py").read_text()
    migration = (ROOT / "sql/analytics/121_research_governance_portfolio_v1.sql").read_text()
    assert "AUDIT_PNL_UNITS" in runner
    assert "SYNC_ECONOMIC_HYPOTHESES" in runner
    assert "GOVERN_EXPERIMENTS" in runner
    assert "research_global_experiment_v1" in migration
    assert "research_holdout_snapshot_v1" in migration
    assert "edge_portfolio_selection_v1" in migration


def test_pnl_is_converted_to_money_before_metrics() -> None:
    runner = (ROOT / "src/scripts/build_strategy_execution_runner_v1.py").read_text()
    assert "monetary_scale = filled * multiplier" in runner
    assert "monetary_commission = commission * monetary_scale" in runner


def test_economic_families_include_stocks_and_futures() -> None:
    sync = (ROOT / "src/scripts/sync_economic_hypothesis_algorithms_v1.py").read_text()
    execution = (ROOT / "src/scripts/build_strategy_execution_runner_v1.py").read_text()
    for code in ("EQUITY_LIQUIDITY_REVERSION", "EQUITY_EVENT_GAP", "FUTURES_CARRY_", "FUTURES_SEASONALITY_"):
        assert code in sync
    for code in ("FUTURES_CURVE_CARRY_V1", "CALENDAR_SEASONALITY_V1",
                 "LIQUIDITY_SHOCK_REVERSION_V1", "SESSION_GAP_CONTINUATION_V1"):
        assert code in execution


def test_panel_exposes_governance_and_both_asset_classes() -> None:
    renderer = (ROOT / "src/marketcore/presentation/workspace_v2/renderer/research_v2_domain_renderer.py").read_text()
    for tile in ("global_trials", "holdout", "pnl_units", "equities", "futures", "portfolio"):
        assert f'_tile("{tile}"' in renderer
