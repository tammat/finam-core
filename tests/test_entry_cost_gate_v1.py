from datetime import datetime, timedelta, timezone

from finam_core.execution.entry_cost_gate_v1 import evaluate_entry_cost_gate_v1


def _evaluate(**overrides):
    values = {
        "entry_price": 100.0,
        "target_price": 102.0,
        "qty": 10.0,
        "best_bid": 99.9,
        "best_ask": 100.1,
        "quote_observed_at": datetime(2026, 7, 25, 8, 0, tzinfo=timezone.utc),
        "round_trip_commission_rub": 1.0,
        "minimum_cost_buffer": 1.5,
        "now": datetime(2026, 7, 25, 8, 1, tzinfo=timezone.utc),
    }
    values.update(overrides)
    return evaluate_entry_cost_gate_v1(**values)


def test_allows_only_when_expected_move_exceeds_buffered_costs():
    decision = _evaluate()
    assert decision.allowed is True
    assert decision.reason_code == "COST_BUFFER_PASS"
    assert decision.expected_move_rub == 20.0
    assert round(decision.estimated_cost_rub, 6) == 4.0
    assert round(decision.required_move_rub, 6) == 6.0


def test_blocks_when_expected_move_does_not_cover_buffered_costs():
    decision = _evaluate(target_price=100.2)
    assert decision.allowed is False
    assert decision.reason_code == "EXPECTED_MOVE_BELOW_COST_BUFFER"


def test_blocks_stale_microstructure():
    decision = _evaluate(
        quote_observed_at=datetime(2026, 7, 25, 7, 0, tzinfo=timezone.utc),
    )
    assert decision.allowed is False
    assert decision.reason_code == "MICROSTRUCTURE_STALE"


def test_blocks_missing_target_or_invalid_book():
    assert _evaluate(target_price=0).reason_code == "EXPECTED_MOVE_UNAVAILABLE"
    assert _evaluate(best_bid=100.0, best_ask=100.0).reason_code == (
        "MICROSTRUCTURE_UNAVAILABLE"
    )


def test_accepts_naive_utc_quote_timestamp():
    decision = _evaluate(
        quote_observed_at=datetime(2026, 7, 25, 8, 0),
        now=datetime(2026, 7, 25, 8, 1, tzinfo=timezone.utc),
    )
    assert decision.allowed is True
