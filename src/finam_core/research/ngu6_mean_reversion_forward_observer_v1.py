from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Sequence

from finam_core.research.finam_commission_model_v1 import (
    calculate_round_trip_commission,
)
from finam_core.research.postgresql_edge_backtest_adapter_v1 import (
    Bar,
    apply_slippage,
    mean_reversion_zscore_signal,
)


SOURCE_VERSION = "NGU6_MEAN_REVERSION_FORWARD_OBSERVER_V1"

CANDIDATE_CODE = "NGU6_MEAN_REVERSION_ZSCORE_FORWARD_V1"
FREEZE_COMMIT = "91f908ce"
FREEZE_SHA256 = (
    "37d1c1caa07496a92a4818ac40b72ea959d53464f2c10bfb96c939ba5f24f153"
)

SYMBOL = "NGU6@RTSX"
TIMEFRAME = "M5"

FORWARD_BOUNDARY = datetime(
    2026, 8, 8, 7, 0,
    tzinfo=timezone.utc,
)

LOOKBACK = 10
THRESHOLD = Decimal("2.5")
HOLD_BARS = 5
QUANTITY = Decimal("1")
SLIPPAGE_BPS = Decimal("2.0")
AC100_LOOKBACK = 100

FROZEN_PARAMETERS = {
    "zscore_lookback": LOOKBACK,
    "zscore_entry_threshold": THRESHOLD,
    "hold_bars": HOLD_BARS,
    "allow_short": True,
    "quantity": QUANTITY,
    "slippage_bps": SLIPPAGE_BPS,
    "commission_model": "FINAM_FUTURES_CONFIGURED_V1",
    "futures_fee_evidence_verified": True,
    "futures_broker_fee_per_contract_per_side": Decimal("0.45"),
    "futures_exchange_fee_per_contract_per_side": Decimal("1.49"),
    "futures_other_fee_per_contract_per_side": Decimal("0"),
}


class ForwardObserverContractError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ContractSpecSnapshot:
    contract_spec_id: int
    valid_from: datetime
    valid_to: datetime | None
    tick_size: Decimal
    tick_value: Decimal
    contract_multiplier: Decimal
    source_version: str


@dataclass(frozen=True, slots=True)
class ForwardObservation:
    candidate_code: str
    signal_ts: datetime
    side: str
    market_entry_price: Decimal
    entry_price: Decimal
    exit_ts: datetime | None
    market_exit_price: Decimal | None
    exit_price: Decimal | None
    gross_pnl: Decimal | None
    commission: Decimal | None
    slippage: Decimal | None
    net_pnl: Decimal | None
    ac100: Decimal | None
    contract_spec: ContractSpecSnapshot
    status: str
    shadow_only: bool = True
    broker_order_sent: bool = False
    runtime_allowed: bool = False
    execution_enabled: bool = False


def rolling_return_autocorrelation(
    bars: Sequence[Bar],
    index: int,
    lookback: int = AC100_LOOKBACK,
) -> Decimal | None:
    # Только returns, полностью известные ДО signal bar.
    if index < lookback + 1:
        return None

    returns: list[float] = []

    start = index - lookback

    for position in range(start, index):
        previous = bars[position - 1].close

        if previous == 0:
            continue

        returns.append(
            float(
                bars[position].close / previous
                - Decimal("1")
            )
        )

    if len(returns) < 3:
        return None

    x = returns[:-1]
    y = returns[1:]

    x_mean = sum(x) / len(x)
    y_mean = sum(y) / len(y)

    numerator = sum(
        (a - x_mean) * (b - y_mean)
        for a, b in zip(x, y)
    )

    dx = sum((a - x_mean) ** 2 for a in x)
    dy = sum((b - y_mean) ** 2 for b in y)

    denominator = math.sqrt(dx * dy)

    if denominator == 0:
        return None

    return Decimal(str(numerator / denominator))


def monetary_pnl(
    *,
    side: str,
    entry_price: Decimal,
    exit_price: Decimal,
    quantity: Decimal,
    contract_multiplier: Decimal,
) -> Decimal:
    if contract_multiplier <= 0:
        raise ForwardObserverContractError(
            "contract_multiplier_not_positive"
        )

    if side == "LONG":
        delta = exit_price - entry_price
    elif side == "SHORT":
        delta = entry_price - exit_price
    else:
        raise ForwardObserverContractError(
            f"unsupported_side:{side}"
        )

    return delta * quantity * contract_multiplier


def build_forward_observations(
    bars: Sequence[Bar],
    contract_specs_by_ts: dict[datetime, ContractSpecSnapshot],
) -> list[ForwardObservation]:
    observations: list[ForwardObservation] = []

    index = 1

    while index < len(bars):
        bar = bars[index]

        # Warm-up history is allowed, signals are not.
        if bar.ts <= FORWARD_BOUNDARY:
            index += 1
            continue

        signal = mean_reversion_zscore_signal(
            bars,
            index,
            FROZEN_PARAMETERS,
        )

        if signal is None:
            index += 1
            continue

        contract_spec = contract_specs_by_ts.get(bar.ts)

        if contract_spec is None:
            raise ForwardObserverContractError(
                f"contract_spec_missing:{bar.ts.isoformat()}"
            )

        market_entry = bar.close

        entry_order_side = (
            "BUY"
            if signal == "LONG"
            else "SELL"
        )

        entry_price = apply_slippage(
            market_entry,
            entry_order_side,
            SLIPPAGE_BPS,
        )

        ac100 = rolling_return_autocorrelation(
            bars,
            index,
        )

        exit_index = index + HOLD_BARS

        if exit_index >= len(bars):
            observations.append(
                ForwardObservation(
                    candidate_code=CANDIDATE_CODE,
                    signal_ts=bar.ts,
                    side=signal,
                    market_entry_price=market_entry,
                    entry_price=entry_price,
                    exit_ts=None,
                    market_exit_price=None,
                    exit_price=None,
                    gross_pnl=None,
                    commission=None,
                    slippage=None,
                    net_pnl=None,
                    ac100=ac100,
                    contract_spec=contract_spec,
                    status="OPEN",
                )
            )
            break

        exit_bar = bars[exit_index]
        market_exit = exit_bar.close

        exit_order_side = (
            "SELL"
            if signal == "LONG"
            else "BUY"
        )

        exit_price = apply_slippage(
            market_exit,
            exit_order_side,
            SLIPPAGE_BPS,
        )

        gross_pnl = monetary_pnl(
            side=signal,
            entry_price=entry_price,
            exit_price=exit_price,
            quantity=QUANTITY,
            contract_multiplier=contract_spec.contract_multiplier,
        )

        market_pnl = monetary_pnl(
            side=signal,
            entry_price=market_entry,
            exit_price=market_exit,
            quantity=QUANTITY,
            contract_multiplier=contract_spec.contract_multiplier,
        )

        slippage = max(
            Decimal("0"),
            market_pnl - gross_pnl,
        )

        commission_breakdown = calculate_round_trip_commission(
            entry_price=entry_price,
            exit_price=exit_price,
            quantity_units=QUANTITY,
            parameters=FROZEN_PARAMETERS,
        )

        commission = commission_breakdown.round_trip_total
        net_pnl = gross_pnl - commission

        observations.append(
            ForwardObservation(
                candidate_code=CANDIDATE_CODE,
                signal_ts=bar.ts,
                side=signal,
                market_entry_price=market_entry,
                entry_price=entry_price,
                exit_ts=exit_bar.ts,
                market_exit_price=market_exit,
                exit_price=exit_price,
                gross_pnl=gross_pnl,
                commission=commission,
                slippage=slippage,
                net_pnl=net_pnl,
                ac100=ac100,
                contract_spec=contract_spec,
                status="CLOSED",
            )
        )

        # Полная parity с historical build_trades():
        # никаких пересекающихся hypothetical positions.
        index = exit_index + 1

    return observations
