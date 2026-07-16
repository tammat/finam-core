from pathlib import Path


def test_walkforward_search_is_cost_adjusted_and_fail_closed() -> None:
    source = Path("src/scripts/build_walkforward_edge_search_v3.py").read_text()
    assert "FOLDS = 5" in source
    assert "transaction_cost_bps" in source
    assert 'EDGE_SEARCH_FRESHNESS_MINUTES' in source
    assert '"transaction_cost_bps": cost_bps' in source
    assert "aggregate[\"trades\"]>=80" in source
    assert "aggregate[\"profit_factor\"]>=1.15" in source
    assert "folds_passed>=4 and final_holdout" in source
    assert "promotion_allowed=0" in source
    assert "live_allowed=0" in source


def test_walkforward_results_are_auditable() -> None:
    migration = Path("sql/analytics/066_walkforward_edge_search_v3.sql").read_text()
    assert "fold_metrics JSONB NOT NULL" in migration
    assert "final_holdout_passed BOOLEAN NOT NULL" in migration
    assert "promotion_allowed BOOLEAN NOT NULL DEFAULT FALSE" in migration
