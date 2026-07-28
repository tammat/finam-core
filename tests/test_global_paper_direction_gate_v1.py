from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_generic_paper_route_applies_symmetric_direction_gate_before_execution():
    text = (ROOT / "src/finam_core/pipelines/paper_pipeline.py").read_text()
    gate_call = "direction_allowed, direction_reason = self._db_intent_direction_gate_v1(intent)"
    execute_call = "raw_fill = self.paper.execute(intent, st)"

    assert "if not is_exit_intent:" in text
    assert gate_call in text
    assert "self._reject_persisted_signal_v1(intent, direction_reason)" in text
    gate_offset = text.index(gate_call)
    assert gate_offset < text.index(execute_call, gate_offset)


def test_generic_direction_gate_is_symmetric_and_db_driven():
    text = (ROOT / "src/finam_core/pipelines/paper_pipeline.py").read_text()

    assert "countertrend_long_allowed, countertrend_short_allowed" in text
    assert "LONG_BLOCKED_CONFIRMED_DOWNTREND" in text
    assert "SHORT_BLOCKED_CONFIRMED_UPTREND" in text
    assert "DIRECTION_REGIME_NOT_READY" in text


def test_direction_policy_can_follow_strategy_timeframe_when_quote_alias_is_generic():
    text = (ROOT / "src/finam_core/pipelines/paper_pipeline.py").read_text()
    start = text.index("    def _db_intent_direction_gate_v1(")
    end = text.index("\n    def ", start + 10)
    body = text[start:end]

    assert 'strategy = str(intent.get("strategy")' in body
    assert "(timeframe = %s OR strategy_code = %s)" in body
    assert "ORDER BY (timeframe = %s) DESC" in body
