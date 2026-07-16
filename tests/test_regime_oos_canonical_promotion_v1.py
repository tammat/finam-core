from pathlib import Path


def test_promotion_requires_cost_adjusted_repeatable_oos_pass() -> None:
    source = Path("src/scripts/promote_regime_oos_to_canonical_v1.py").read_text()
    assert "transaction_cost_bps>=8" in source
    assert "oos_trades>=30" in source
    assert "oos_profit_factor>=1.20" in source
    assert "folds_passed>=2" in source
    assert "repeat_runs" in source and "< 3" in source
    assert '"regime_code": row["regime_code"]' in source
    assert "paper_allowed=0" in source
    assert "runtime_allowed=0" in source
    assert "live_allowed=0" in source
    assert "OOS_MARKET_DATA_STALE_AT_PROMOTION" in source
    assert "interval '15 minutes'" in source
