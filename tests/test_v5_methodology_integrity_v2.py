from pathlib import Path

from scripts.run_v5_purged_oos_worker_v1 import _context


def test_outcome_cannot_change_frozen_exit_cohort() -> None:
    trade = {"strategy":"S","side":"LONG","entry_regime":"RANGE",
             "payload":{"context":{"planned_exit_rule":"STOP_TAKE",
                                     "actual_exit_reason":"time_exit"}}}
    assert _context(trade)["exit"] == "STOP_TAKE"


def test_v5_cost_guard_is_conservative_and_fail_closed() -> None:
    sql = Path("sql/analytics/234_v5_methodology_integrity_v2.sql").read_text()
    assert "2*spec.one_tick_cost*abs(c.qty)" in sql
    assert "CONSERVATIVE_SPREAD_SLIPPAGE_FLOOR_UNAVAILABLE" in sql
    assert "planned_exit_rule" in sql


def test_oos_uses_effective_event_count_and_no_global_claim_order() -> None:
    worker = Path("src/scripts/run_v5_purged_oos_worker_v1.py").read_text()
    migration = Path("sql/analytics/234_v5_methodology_integrity_v2.sql").read_text()
    assert "GROUP BY event_cluster_id" in worker
    assert "effective_observations" in worker
    assert "DROP INDEX IF EXISTS analytics.v5_oos_included_trade_once_idx" in migration
    assert "ORDER BY created_at" not in worker
