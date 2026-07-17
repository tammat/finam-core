from pathlib import Path


def test_walkforward_search_is_cost_adjusted_and_fail_closed() -> None:
    source = Path("src/scripts/build_walkforward_edge_search_v3.py").read_text()
    assert "FOLDS = 5" in source
    assert "transaction_cost_bps" in source
    assert 'EDGE_SEARCH_FRESHNESS_MINUTES' in source
    assert '"transaction_cost_bps": cost_bps' in source
    assert 'configuration["gate_policy"]["walkforward"]' in source
    assert 'walkforward_gate["min_trades"]' in source
    assert 'walkforward_gate["min_profit_factor"]' in source
    assert 'walkforward_gate["min_folds_passed"]' in source
    assert 'walkforward_gate["final_holdout_required"]' in source
    assert "promotion_allowed=0" in source
    assert "live_allowed=0" in source
    assert "NEGATIVE_COST_ADJUSTED_EXPECTANCY" in source
    assert "WALKFORWARD_FOLDS_UNSTABLE" in source
    assert "FINAL_HOLDOUT_FAILED" in source


def test_regime_search_requires_auditable_futures_contract() -> None:
    source = Path("src/scripts/build_edge_regime_hypothesis_discovery_v2.py").read_text()
    universe = Path("src/scripts/edge_research_universe_v1.py").read_text()
    assert "futures_contract_calendar" in universe
    assert "futures_contract_universe" in universe
    assert "contract_expiration" in source
    assert "coalesce(c.expiration_date,u.expiration_date)>=current_date" in universe


def test_walkforward_results_are_auditable() -> None:
    migration = Path("sql/analytics/066_walkforward_edge_search_v3.sql").read_text()
    assert "fold_metrics JSONB NOT NULL" in migration
    assert "final_holdout_passed BOOLEAN NOT NULL" in migration
    assert "promotion_allowed BOOLEAN NOT NULL DEFAULT FALSE" in migration
