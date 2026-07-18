from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts.build_strategy_execution_runner_v1 import Bar, Trade
from scripts.build_walkforward_edge_search_v3 import methodology_evidence
from scripts.evaluate_edge_methodology_contract_v1 import are_neighbors,bh_q_values,correlation,parameter_core,portfolio_daily_pnl


ROOT = Path(__file__).resolve().parents[1]


def test_benjamini_hochberg_controls_multiple_testing() -> None:
    q = bh_q_values([0.001,0.01,0.20,0.80])
    assert q[0] <= q[1] <= q[2] <= q[3]
    assert round(q[0],3) == 0.004
    assert round(q[1],3) == 0.020


def test_parameter_robustness_uses_neighbors_not_identical_peak() -> None:
    base={"lookback":40,"hold":5,"threshold":1.0}
    assert are_neighbors(base,{**base,"threshold":1.2})
    assert not are_neighbors(base,base)
    assert not are_neighbors(base,{**base,"threshold":1.2,"hold":9})
    assert parameter_core({**base,"commission":10,"slippage":2}) == base


def test_walkforward_persists_execution_capacity_and_daily_evidence() -> None:
    start=datetime(2026,1,1,tzinfo=timezone.utc)
    bars=[Bar(start+timedelta(minutes=5*i),100+i*.1,1000000) for i in range(100)]
    trades=[Trade(1,"BUY",bars[20].ts,bars[25].ts,102,104,2,.1,0,1.9),
            Trade(2,"BUY",bars[40].ts,bars[45].ts,104,105,1,.1,0,.9)]
    evidence=methodology_evidence(trades,bars)
    assert evidence["stress_cost_multiplier"] == 1.5
    assert evidence["stressed_profit_factor"] > 0
    assert evidence["capacity_rub"] >= 500000
    assert evidence["daily_pnl"]


def test_portfolio_correlation_requires_overlap() -> None:
    value,overlap=correlation({"a":1,"b":2,"c":3},{"a":3,"b":2,"c":1})
    assert overlap == 3 and value == -1
    assert correlation({"a":1},{"a":2}) == (None,1)


def test_portfolio_daily_pnl_query_executes_on_postgres() -> None:
    import psycopg2
    import psycopg2.extras

    with psycopg2.connect("postgresql:///finam_core") as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            daily_pnl, portfolio_exists = portfolio_daily_pnl(cursor)

    assert isinstance(daily_pnl, dict)
    assert isinstance(portfolio_exists, bool)


def test_active_portfolio_with_short_history_is_not_treated_as_empty() -> None:
    evaluator=(ROOT/"src/scripts/evaluate_edge_methodology_contract_v1.py").read_text()
    assert "portfolio_exists" in evaluator
    assert "not portfolio_exists" in evaluator
    assert '"empty_portfolio":not portfolio_exists' in evaluator


def test_contract_is_six_stage_and_precedes_promotion() -> None:
    sql=(ROOT/"sql/analytics/090_edge_methodology_contract_v1.sql").read_text()
    runner=(ROOT/"src/scripts/run_autonomous_edge_search_cycle_v1.py").read_text()
    promoter=(ROOT/"src/scripts/promote_regime_oos_to_canonical_v1.py").read_text()
    for gate in ("STATISTICAL_SIGNIFICANCE","PARAMETER_ROBUSTNESS","INDEPENDENT_HOLDOUT",
                 "REALISTIC_EXECUTION","CAPACITY","PORTFOLIO_CONTRIBUTION"):
        assert gate in sql
    assert "METHODOLOGY_GATE" in runner
    assert "edge_methodology_evaluation_v1" in promoter
    assert "m.verdict_code='PASS'" in promoter
    assert "m.parameter_core=h.parameter_json" in promoter
    assert "EDGE_METHODOLOGY_CONTRACT_IMMUTABLE" in sql
    assert "edge_methodology_one_active_contract_v1" in sql
    assert "IF NOT EXISTS (SELECT 1 FROM analytics.edge_search_scenario_step_v1" in sql


def test_holdout_consumption_is_unique_and_promotion_remains_false() -> None:
    sql=(ROOT/"sql/analytics/090_edge_methodology_contract_v1.sql").read_text()
    evaluator=(ROOT/"src/scripts/evaluate_edge_methodology_contract_v1.py").read_text()
    assert "UNIQUE(strategy_code,symbol,timeframe,parameter_hash,holdout_end)" in sql
    assert "all_gates_required=1" in evaluator
    assert "promotion_allowed=0" in evaluator
    assert "stressed_profit_factor" in evaluator
