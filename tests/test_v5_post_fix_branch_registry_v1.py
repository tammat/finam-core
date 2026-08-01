from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_four_prospective_branches_are_frozen_and_safe():
    source = (ROOT / "src/scripts/register_v5_post_fix_branches_v1.py").read_text()
    for code in (
        "SBER_LONG_M5_POST_FIX_V1", "BRQ6_SHORT_M5_POST_FIX_V1",
        "GLDRUBF_LONG_M5_POST_FIX_V1", "CNYRUBF_LONG_M5_POST_FIX_V1",
    ):
        assert code in source
    assert '"promotion_allowed": False' in source
    assert '"paper_allowed": False' in source
    assert '"real_trading_allowed": False' in source
    assert '"observation_symbol": branch["observation"]' in source
    assert '"minimum_closed_trades": 20' in source


def test_gold_uses_logical_perpetual_and_active_contract_observations():
    source = (ROOT / "src/scripts/register_v5_post_fix_branches_v1.py").read_text()
    assert 'logical="GLDRUBF@RTSX", observation="GDU6@RTSX"' in source
    worker = (ROOT / "src/scripts/run_v5_purged_oos_worker_v1.py").read_text()
    assert 'request.get("observation_symbol", request["symbol"])' in worker


def test_registry_rejects_parameter_mutation():
    sql = (ROOT / "sql/analytics/260_v5_post_fix_branch_registry_v1.sql").read_text()
    assert "reject_frozen_branch_mutation_v1" in sql
    assert "frozen profile is immutable" in sql
    assert "CHECK (paper_allowed = false)" in sql
    assert "CHECK (real_allowed = false)" in sql


def test_worker_cold_start_aggregate_always_returns_a_row():
    worker = (ROOT / "src/scripts/run_v5_purged_oos_worker_v1.py").read_text()
    assert "CROSS JOIN LATERAL" not in worker
    assert "WHERE run_id=%s AND decision_code<>'INCLUDED'" in worker
