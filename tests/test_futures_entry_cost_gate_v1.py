from datetime import datetime, timedelta, timezone

import pytest

from finam_core.execution.futures_entry_cost_gate_v1 import (
    evaluate_futures_entry_cost_gate_v1,
)


def test_futures_gate_converts_price_move_and_spread_to_rubles() -> None:
    now = datetime.now(timezone.utc)
    decision = evaluate_futures_entry_cost_gate_v1(
        entry_price=80.00,
        target_price=80.20,
        qty=2,
        best_bid=79.99,
        best_ask=80.00,
        quote_observed_at=now,
        min_price_step=0.01,
        step_value=10.0,
        round_trip_commission_rub=8.0,
        minimum_cost_buffer=1.5,
        now=now,
    )

    assert decision.allowed is True
    assert decision.expected_move_rub == pytest.approx(400.0)
    assert decision.estimated_cost_rub == pytest.approx(38.0)
    assert decision.required_move_rub == pytest.approx(57.0)


def test_futures_gate_rejects_stale_book() -> None:
    now = datetime.now(timezone.utc)
    decision = evaluate_futures_entry_cost_gate_v1(
        entry_price=80.00,
        target_price=81.00,
        qty=1,
        best_bid=79.99,
        best_ask=80.00,
        quote_observed_at=now - timedelta(minutes=10),
        min_price_step=0.01,
        step_value=10.0,
        round_trip_commission_rub=4.0,
        minimum_cost_buffer=1.5,
        now=now,
    )

    assert decision.allowed is False
    assert decision.reason_code == "MICROSTRUCTURE_STALE"


def test_futures_gate_rejects_missing_contract_spec() -> None:
    now = datetime.now(timezone.utc)
    decision = evaluate_futures_entry_cost_gate_v1(
        entry_price=80.00,
        target_price=81.00,
        qty=1,
        best_bid=79.99,
        best_ask=80.00,
        quote_observed_at=now,
        min_price_step=0,
        step_value=0,
        round_trip_commission_rub=4.0,
        minimum_cost_buffer=1.5,
        now=now,
    )

    assert decision.allowed is False
    assert decision.reason_code == "FUTURES_SPEC_UNAVAILABLE"
