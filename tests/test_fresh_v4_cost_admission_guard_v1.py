from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_v4_cost_guard_is_strict_and_db_driven() -> None:
    sql = (ROOT / "sql/analytics/201_fresh_v4_cost_admission_guard_v1.sql").read_text()
    assert "fresh_v4_cost_admission_policy_v1" in sql
    assert "'STRICT_OOS_V1',80,1.15,0,1.50" in sql
    assert "average_execution_cost * p.cost_buffer_multiplier" in sql
    assert "REJECTED_COSTS" in sql
    assert "ELIGIBLE_OOS" in sql


def test_oos_admission_requires_v5_cost_pass() -> None:
    source = (ROOT / "src/scripts/admit_trade_outcome_hypotheses_to_oos_v1.py").read_text()
    assert "fresh_v5_frozen_cost_admission_guard_v2" in source
    assert "fresh_v4_cost_admission_guard_v1" not in source
    assert 'cost_status != "ELIGIBLE_OOS"' in source
    assert '"REJECTED_COSTS"' in source
    assert '"fresh_cohort": "FRESH_V5_CONFIRM"' in source
    assert '"v5_closed_trades": v5_trades' in source
    assert "fresh_v5_early_loss_quarantine_v1" in source
    assert '"policy": "PURGED_EMBARGO_V5_V1"' in source
    assert '"future_data_only": True' in source
    assert '"purge_before_ts"' in source
    assert '"confirmation_after_ts"' in source
    assert "max_holding_seconds" in source
    assert 'if bool(row["early_quarantined"])' in source


def test_frozen_v5_guard_excludes_oos_from_training() -> None:
    sql=(ROOT/"sql/analytics/233_fresh_v5_frozen_cost_guard_v2.sql").read_text()
    assert "closed_trades_fresh_v5_training_v1" in sql
    assert "V5_FROZEN_COST_AND_EXPECTANCY_CONFIRMED" in sql


def test_v5_guard_is_isolated_strict_and_has_no_pf_999_sentinel() -> None:
    sql = (ROOT / "sql/analytics/208_fresh_v5_cost_admission_guard_v1.sql").read_text()
    assert "closed_trades_fresh_v5_confirmed" in sql
    assert "closed_trades_fresh_v4_assigned" not in sql
    assert "'STRICT_OOS_V5', 80, 1.15, 0, 1.50" in sql
    assert "net_profit_factor IS NULL" in sql
    assert "THEN 999" not in sql
    assert "fresh_v5_early_loss_quarantine_v1" in sql


def test_early_loss_quarantine_is_db_driven_and_keeps_oos_sample_at_80() -> None:
    sql = (ROOT / "sql/analytics/202_fresh_v4_early_loss_quarantine_v1.sql").read_text()
    assert "'STRICT_EARLY_V1',20,0.80,1.50" in sql
    assert "fresh_v4_early_loss_quarantine_v1" in sql
    assert "THEN true" in sql
    assert "'EARLY_NEGATIVE_AFTER_COSTS'" in sql
    assert "fresh_v4_cost_admission_guard_v1" in sql
