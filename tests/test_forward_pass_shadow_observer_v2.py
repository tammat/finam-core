from pathlib import Path


def test_observer_requires_forward_pass_and_future_observations() -> None:
    source=Path("src/scripts/run_forward_pass_shadow_observer_v2.py").read_text()
    assert "g.decision_code=p.source_decision_code" in source
    assert "g.review_eligible" in source
    assert "signal_ts>%s" in source
    assert "observation_not_before" in source


def test_observer_is_idempotent_and_never_executes() -> None:
    source=Path("src/scripts/run_forward_pass_shadow_observer_v2.py").read_text()
    assert "execution_fingerprint TEXT NOT NULL UNIQUE" in Path("sql/analytics/079_forward_pass_shadow_observer_v2.sql").read_text()
    assert "ON CONFLICT(execution_fingerprint) DO UPDATE" in source
    assert "broker_order_sent=FALSE,runtime_allowed=FALSE" in source
    assert 'print("broker_orders=0")' in source


def test_system_cycle_and_paper_admission_use_v2() -> None:
    cycle=Path("src/scripts/run_autonomous_edge_search_cycle_v1.py").read_text()
    admission=Path("src/scripts/build_profit_funnel_shadow_paper_admission_v2.py").read_text()
    assert '"PROJECT_SHADOW": "src/scripts/run_forward_pass_shadow_observer_v2.py"' in cycle
    assert "analytics.forward_pass_shadow_observation_v1" in admission
    assert "analytics.forward_edge_shadow_trade_v1" not in admission
