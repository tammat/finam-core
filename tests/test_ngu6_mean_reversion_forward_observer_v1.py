from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch

import pytest

from finam_core.research.ngu6_mean_reversion_forward_observer_v1 import (
    CANDIDATE_CODE,
    FORWARD_BOUNDARY,
    FROZEN_PARAMETERS,
    ContractSpecSnapshot,
    ForwardObserverContractError,
    build_forward_observations,
    monetary_pnl,
)
from finam_core.research.postgresql_edge_backtest_adapter_v1 import (
    Bar,
    apply_slippage,
    mean_reversion_zscore_signal,
)


def make_bar(ts, close):
    price = Decimal(str(close))
    return Bar(
        ts=ts,
        open=price,
        high=price,
        low=price,
        close=price,
        volume=Decimal("1"),
    )


def make_spec(ts, multiplier="8000"):
    return ContractSpecSnapshot(
        contract_spec_id=1,
        valid_from=ts - timedelta(days=1),
        valid_to=None,
        tick_size=Decimal("0.001"),
        tick_value=Decimal("8"),
        contract_multiplier=Decimal(multiplier),
        source_version="TEST_SPEC_V1",
    )


def make_bars(
    *,
    before=20,
    after=20,
    start_price=Decimal("3.000"),
):
    start = FORWARD_BOUNDARY - timedelta(
        minutes=5 * before
    )

    bars = []

    for i in range(before + after + 1):
        # Небольшое движение, конкретный сигнал в тестах
        # при необходимости мокается.
        close = start_price + Decimal(i) * Decimal("0.001")
        bars.append(
            make_bar(
                start + timedelta(minutes=5 * i),
                close,
            )
        )

    return bars


def spec_map(bars):
    return {
        bar.ts: make_spec(bar.ts)
        for bar in bars
        if bar.ts > FORWARD_BOUNDARY
    }


def test_boundary_is_strictly_exclusive():
    bars = make_bars(before=20, after=10)

    def signal(_, index, __):
        if bars[index].ts == FORWARD_BOUNDARY:
            return "LONG"
        return None

    with patch(
        "finam_core.research."
        "ngu6_mean_reversion_forward_observer_v1."
        "mean_reversion_zscore_signal",
        side_effect=signal,
    ):
        observations = build_forward_observations(
            bars,
            spec_map(bars),
        )

    assert observations == []


def test_first_post_boundary_signal_is_allowed():
    bars = make_bars(before=20, after=10)
    target = FORWARD_BOUNDARY + timedelta(minutes=5)

    def signal(_, index, __):
        if bars[index].ts == target:
            return "LONG"
        return None

    with patch(
        "finam_core.research."
        "ngu6_mean_reversion_forward_observer_v1."
        "mean_reversion_zscore_signal",
        side_effect=signal,
    ):
        observations = build_forward_observations(
            bars,
            spec_map(bars),
        )

    assert len(observations) == 1

    obs = observations[0]

    assert obs.signal_ts == target
    assert obs.status == "CLOSED"
    assert obs.candidate_code == CANDIDATE_CODE

    assert obs.shadow_only is True
    assert obs.broker_order_sent is False
    assert obs.runtime_allowed is False
    assert obs.execution_enabled is False


def test_open_observation_when_five_future_bars_missing():
    bars = make_bars(before=20, after=3)
    target = FORWARD_BOUNDARY + timedelta(minutes=5)

    def signal(_, index, __):
        if bars[index].ts == target:
            return "SHORT"
        return None

    with patch(
        "finam_core.research."
        "ngu6_mean_reversion_forward_observer_v1."
        "mean_reversion_zscore_signal",
        side_effect=signal,
    ):
        observations = build_forward_observations(
            bars,
            spec_map(bars),
        )

    assert len(observations) == 1

    obs = observations[0]

    assert obs.status == "OPEN"
    assert obs.side == "SHORT"
    assert obs.exit_ts is None
    assert obs.net_pnl is None
    assert obs.contract_spec.contract_spec_id == 1


def test_commission_and_monetary_math_match_frozen_contract():
    entry_market = Decimal("3.000")
    exit_market = Decimal("3.020")
    multiplier = Decimal("8000")

    entry = apply_slippage(
        entry_market,
        "BUY",
        Decimal("2.0"),
    )
    exit_ = apply_slippage(
        exit_market,
        "SELL",
        Decimal("2.0"),
    )

    gross = monetary_pnl(
        side="LONG",
        entry_price=entry,
        exit_price=exit_,
        quantity=Decimal("1"),
        contract_multiplier=multiplier,
    )

    assert gross == (
        (exit_ - entry) * multiplier
    )

    # Frozen FINAM futures commission:
    # (0.45 + 1.49) * 2 sides = 3.88 RUB.
    from finam_core.research.finam_commission_model_v1 import (
        calculate_round_trip_commission,
    )

    breakdown = calculate_round_trip_commission(
        entry_price=entry,
        exit_price=exit_,
        quantity_units=1,
        parameters=FROZEN_PARAMETERS,
    )

    assert breakdown.round_trip_total == Decimal("3.88")


def test_non_overlapping_positions():
    bars = make_bars(before=20, after=20)

    first = FORWARD_BOUNDARY + timedelta(minutes=5)
    overlapping = FORWARD_BOUNDARY + timedelta(minutes=10)
    second_allowed = FORWARD_BOUNDARY + timedelta(minutes=35)

    def signal(_, index, __):
        ts = bars[index].ts

        if ts in (first, overlapping, second_allowed):
            return "LONG"

        return None

    with patch(
        "finam_core.research."
        "ngu6_mean_reversion_forward_observer_v1."
        "mean_reversion_zscore_signal",
        side_effect=signal,
    ):
        observations = build_forward_observations(
            bars,
            spec_map(bars),
        )

    assert [o.signal_ts for o in observations] == [
        first,
        second_allowed,
    ]


def test_missing_contract_spec_fails_closed():
    bars = make_bars(before=20, after=10)
    target = FORWARD_BOUNDARY + timedelta(minutes=5)

    def signal(_, index, __):
        if bars[index].ts == target:
            return "LONG"
        return None

    with patch(
        "finam_core.research."
        "ngu6_mean_reversion_forward_observer_v1."
        "mean_reversion_zscore_signal",
        side_effect=signal,
    ):
        with pytest.raises(
            ForwardObserverContractError,
            match="contract_spec_missing",
        ):
            build_forward_observations(
                bars,
                {},
            )


def test_real_signal_primitive_uses_frozen_parameters():
    # 9 closes около 3.0 + резкое снижение текущего close.
    # Текущий бар входит в rolling z-score, как в historical engine.
    start = FORWARD_BOUNDARY - timedelta(minutes=45)

    closes = [
        Decimal("3.000"),
        Decimal("3.001"),
        Decimal("2.999"),
        Decimal("3.000"),
        Decimal("3.001"),
        Decimal("3.000"),
        Decimal("2.999"),
        Decimal("3.000"),
        Decimal("3.001"),
        Decimal("2.900"),
    ]

    bars = [
        make_bar(
            start + timedelta(minutes=5 * i),
            close,
        )
        for i, close in enumerate(closes)
    ]

    signal = mean_reversion_zscore_signal(
        bars,
        len(bars) - 1,
        FROZEN_PARAMETERS,
    )

    assert signal == "LONG"
