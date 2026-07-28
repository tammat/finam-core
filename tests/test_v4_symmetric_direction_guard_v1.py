from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_runtime_gate_is_symmetric_and_db_driven():
    text = (ROOT / "src/finam_core/pipelines/paper_pipeline.py").read_text()
    equity_cost = (ROOT / "src/finam_core/execution/entry_cost_gate_v1.py").read_text()
    futures_cost = (ROOT / "src/finam_core/execution/futures_entry_cost_gate_v1.py").read_text()
    assert "countertrend_long_allowed" in text
    assert "countertrend_short_allowed" in text
    assert "LONG_BLOCKED_CONFIRMED_DOWNTREND" in text
    assert "SHORT_BLOCKED_CONFIRMED_UPTREND" in text
    assert "CANDLE_REGIME_NOT_READY" in text
    assert "EXPECTED_MOVE_BELOW_COST_BUFFER" in equity_cost
    assert "EXPECTED_MOVE_BELOW_FUTURES_COST_BUFFER" in futures_cost


def test_oos_guard_blocks_ordinary_short_against_uptrend():
    text = (ROOT / "sql/analytics/203_v4_symmetric_direction_guard_v1.sql").read_text()
    assert "SHORT_IN_CONFIRMED_UPTREND_WITHOUT_COUNTERTREND_MODEL" in text
    assert "VOLATILITY_BREAKOUT_EQUITY" in text
    assert "BR_CONSERVATIVE_BREAKOUT" in text
    assert "NG_CONSERVATIVE_BREAKOUT_M1" in text
