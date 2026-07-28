from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_equity_strategy_has_no_volatility_breakout_fallback() -> None:
    text = (ROOT / "src/finam_core/pipelines/paper_pipeline.py").read_text()
    resolver = text[text.index("def _runtime_strategy_name_for_symbol"):text.index("def _strategy_name_for_symbol")]
    assert 'return "UNASSIGNED"' in resolver
    assert 'return "VOLATILITY_BREAKOUT_EQUITY"' not in resolver


def test_signal_gate_requires_assignment_direction_and_cost_edge() -> None:
    text = (ROOT / "src/finam_core/pipelines/paper_pipeline.py").read_text()
    cost_gate = (ROOT / "src/finam_core/execution/entry_cost_gate_v1.py").read_text()
    assert 'return "UNASSIGNED"' in text
    assert "DIRECTION_POLICY_NOT_FOUND" in text
    assert "LONG_BLOCKED_CONFIRMED_DOWNTREND" in text
    assert "evaluate_entry_cost_gate_v1" in text
    assert "EXPECTED_MOVE_BELOW_COST_BUFFER" in cost_gate
    assert "round_trip_commission_rub" in cost_gate
    assert "slippage_spreads" in cost_gate


def test_migration_assigns_separate_futures_generators_and_oos_guard() -> None:
    text = (ROOT / "sql/analytics/202_v4_strategy_assignment_and_oos_guard_v1.sql").read_text()
    assert "BR_FUTURES_GENERATOR_V1" in text
    assert "NG_FUTURES_GENERATOR_V1" in text
    assert "runtime_strategy_assignment_v1" in text
    assert "oos_branch_guard_v1" in text
    assert "NEGATIVE_EXPECTANCY_LONG_IN_CONFIRMED_DOWNTREND" in text


def test_actual_exit_is_one_of_four_business_classes() -> None:
    text = (ROOT / "src/scripts/analytics/materialize_closed_trades_from_fills_v1.py").read_text()
    for exit_code in ("TIME_EXIT", "TRAILING", "TARGET", "STOP"):
        assert f'exit_rule = "{exit_code}"' in text
