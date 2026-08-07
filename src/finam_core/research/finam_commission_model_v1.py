#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Mapping


MODEL_LEGACY_FIXED_PER_SIDE = "LEGACY_FIXED_PER_SIDE"
MODEL_FINAM_EQUITY_REPORT_PROXY_V1 = (
    "FINAM_EQUITY_REPORT_PROXY_V1"
)
MODEL_FINAM_FUTURES_CONFIGURED_V1 = (
    "FINAM_FUTURES_CONFIGURED_V1"
)

SUPPORTED_MODELS = {
    MODEL_LEGACY_FIXED_PER_SIDE,
    MODEL_FINAM_EQUITY_REPORT_PROXY_V1,
    MODEL_FINAM_FUTURES_CONFIGURED_V1,
}


class CommissionModelContractError(ValueError):
    """Ошибка контракта модели торговых затрат."""


def to_decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value

    if value is None:
        return Decimal("0")

    return Decimal(str(value))


def to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value

    return str(value).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


@dataclass(frozen=True, slots=True)
class CommissionBreakdown:
    model_code: str
    entry_turnover: Decimal
    exit_turnover: Decimal

    entry_broker_fee: Decimal
    exit_broker_fee: Decimal

    entry_settlement_fee: Decimal
    exit_settlement_fee: Decimal

    entry_exchange_fee: Decimal
    exit_exchange_fee: Decimal

    entry_other_fee: Decimal
    exit_other_fee: Decimal

    @property
    def entry_total(self) -> Decimal:
        return (
            self.entry_broker_fee
            + self.entry_settlement_fee
            + self.entry_exchange_fee
            + self.entry_other_fee
        )

    @property
    def exit_total(self) -> Decimal:
        return (
            self.exit_broker_fee
            + self.exit_settlement_fee
            + self.exit_exchange_fee
            + self.exit_other_fee
        )

    @property
    def round_trip_total(self) -> Decimal:
        return self.entry_total + self.exit_total


def normalize_commission_parameters(
    parameters: Mapping[str, Any],
) -> dict[str, Any]:
    normalized = dict(parameters)

    normalized.setdefault(
        "commission_model",
        MODEL_LEGACY_FIXED_PER_SIDE,
    )

    # Наследуемая фиксированная модель.
    normalized.setdefault("commission_per_side", 0.0)

    # Модель для акций по фактическому отчётному proxy.
    normalized.setdefault(
        "broker_order_fee_per_side",
        41.30,
    )
    normalized.setdefault(
        "settlement_fee_rate",
        0.0003,
    )
    normalized.setdefault(
        "exchange_fee_rate",
        0.0,
    )
    normalized.setdefault(
        "other_fee_per_side",
        0.0,
    )

    # Отдельная модель для срочного рынка.
    # Значения не выводятся из акционного отчёта.
    normalized.setdefault(
        "futures_broker_fee_per_contract_per_side",
        0.0,
    )
    normalized.setdefault(
        "futures_exchange_fee_per_contract_per_side",
        0.0,
    )
    normalized.setdefault(
        "futures_other_fee_per_contract_per_side",
        0.0,
    )
    normalized.setdefault(
        "futures_fee_evidence_verified",
        False,
    )

    model_code = str(
        normalized["commission_model"]
    ).strip().upper()

    if model_code not in SUPPORTED_MODELS:
        raise CommissionModelContractError(
            f"unsupported_commission_model:{model_code}"
        )

    normalized["commission_model"] = model_code

    non_negative_fields = (
        "commission_per_side",
        "broker_order_fee_per_side",
        "settlement_fee_rate",
        "exchange_fee_rate",
        "other_fee_per_side",
        "futures_broker_fee_per_contract_per_side",
        "futures_exchange_fee_per_contract_per_side",
        "futures_other_fee_per_contract_per_side",
    )

    for field in non_negative_fields:
        if to_decimal(normalized[field]) < 0:
            raise CommissionModelContractError(
                f"{field}_must_be_non_negative"
            )

    if model_code == MODEL_FINAM_FUTURES_CONFIGURED_V1:
        if not to_bool(
            normalized["futures_fee_evidence_verified"]
        ):
            raise CommissionModelContractError(
                "futures_fee_evidence_not_verified"
            )

        futures_total = (
            to_decimal(
                normalized[
                    "futures_broker_fee_per_contract_per_side"
                ]
            )
            + to_decimal(
                normalized[
                    "futures_exchange_fee_per_contract_per_side"
                ]
            )
            + to_decimal(
                normalized[
                    "futures_other_fee_per_contract_per_side"
                ]
            )
        )

        if futures_total <= 0:
            raise CommissionModelContractError(
                "futures_fee_per_contract_per_side_not_positive"
            )

    return normalized


def calculate_round_trip_commission(
    *,
    entry_price: Decimal | float,
    exit_price: Decimal | float,
    quantity_units: Decimal | float | int,
    parameters: Mapping[str, Any],
) -> CommissionBreakdown:
    normalized = normalize_commission_parameters(parameters)

    model_code = str(normalized["commission_model"])
    entry_price_value = to_decimal(entry_price)
    exit_price_value = to_decimal(exit_price)
    quantity_value = to_decimal(quantity_units)

    if entry_price_value <= 0:
        raise CommissionModelContractError(
            "entry_price_must_be_positive"
        )

    if exit_price_value <= 0:
        raise CommissionModelContractError(
            "exit_price_must_be_positive"
        )

    if quantity_value <= 0:
        raise CommissionModelContractError(
            "quantity_units_must_be_positive"
        )

    entry_turnover = entry_price_value * quantity_value
    exit_turnover = exit_price_value * quantity_value

    if model_code == MODEL_LEGACY_FIXED_PER_SIDE:
        fixed_fee = to_decimal(
            normalized["commission_per_side"]
        )

        return CommissionBreakdown(
            model_code=model_code,
            entry_turnover=entry_turnover,
            exit_turnover=exit_turnover,
            entry_broker_fee=fixed_fee,
            exit_broker_fee=fixed_fee,
            entry_settlement_fee=Decimal("0"),
            exit_settlement_fee=Decimal("0"),
            entry_exchange_fee=Decimal("0"),
            exit_exchange_fee=Decimal("0"),
            entry_other_fee=Decimal("0"),
            exit_other_fee=Decimal("0"),
        )

    if model_code == MODEL_FINAM_EQUITY_REPORT_PROXY_V1:
        broker_fee = to_decimal(
            normalized["broker_order_fee_per_side"]
        )
        settlement_rate = to_decimal(
            normalized["settlement_fee_rate"]
        )
        exchange_rate = to_decimal(
            normalized["exchange_fee_rate"]
        )
        other_fee = to_decimal(
            normalized["other_fee_per_side"]
        )

        return CommissionBreakdown(
            model_code=model_code,
            entry_turnover=entry_turnover,
            exit_turnover=exit_turnover,
            entry_broker_fee=broker_fee,
            exit_broker_fee=broker_fee,
            entry_settlement_fee=(
                entry_turnover * settlement_rate
            ),
            exit_settlement_fee=(
                exit_turnover * settlement_rate
            ),
            entry_exchange_fee=(
                entry_turnover * exchange_rate
            ),
            exit_exchange_fee=(
                exit_turnover * exchange_rate
            ),
            entry_other_fee=other_fee,
            exit_other_fee=other_fee,
        )

    # Для фьючерсов quantity_units означает число контрактов.
    broker_per_contract = to_decimal(
        normalized[
            "futures_broker_fee_per_contract_per_side"
        ]
    )
    exchange_per_contract = to_decimal(
        normalized[
            "futures_exchange_fee_per_contract_per_side"
        ]
    )
    other_per_contract = to_decimal(
        normalized[
            "futures_other_fee_per_contract_per_side"
        ]
    )

    return CommissionBreakdown(
        model_code=model_code,
        entry_turnover=entry_turnover,
        exit_turnover=exit_turnover,
        entry_broker_fee=(
            broker_per_contract * quantity_value
        ),
        exit_broker_fee=(
            broker_per_contract * quantity_value
        ),
        entry_settlement_fee=Decimal("0"),
        exit_settlement_fee=Decimal("0"),
        entry_exchange_fee=(
            exchange_per_contract * quantity_value
        ),
        exit_exchange_fee=(
            exchange_per_contract * quantity_value
        ),
        entry_other_fee=(
            other_per_contract * quantity_value
        ),
        exit_other_fee=(
            other_per_contract * quantity_value
        ),
    )


def self_test() -> int:
    legacy = calculate_round_trip_commission(
        entry_price=Decimal("300"),
        exit_price=Decimal("301"),
        quantity_units=Decimal("10"),
        parameters={
            "commission_model": MODEL_LEGACY_FIXED_PER_SIDE,
            "commission_per_side": Decimal("1.5"),
        },
    )

    assert legacy.round_trip_total == Decimal("3.0")

    equity = calculate_round_trip_commission(
        entry_price=Decimal("295.01"),
        exit_price=Decimal("295.01"),
        quantity_units=Decimal("20"),
        parameters={
            "commission_model": (
                MODEL_FINAM_EQUITY_REPORT_PROXY_V1
            ),
            "broker_order_fee_per_side": Decimal("41.30"),
            "settlement_fee_rate": Decimal("0.0003"),
            "exchange_fee_rate": Decimal("0"),
            "other_fee_per_side": Decimal("0"),
        },
    )

    assert equity.entry_total == Decimal("43.070060")
    assert equity.round_trip_total == Decimal("86.140120")

    futures = calculate_round_trip_commission(
        entry_price=Decimal("95"),
        exit_price=Decimal("96"),
        quantity_units=Decimal("5"),
        parameters={
            "commission_model": (
                MODEL_FINAM_FUTURES_CONFIGURED_V1
            ),
            "futures_broker_fee_per_contract_per_side": (
                Decimal("1.20")
            ),
            "futures_exchange_fee_per_contract_per_side": (
                Decimal("0.50")
            ),
            "futures_other_fee_per_contract_per_side": (
                Decimal("0.10")
            ),
            "futures_fee_evidence_verified": True,
        },
    )

    # 5 контрактов × (1.20 + 0.50 + 0.10) × 2 стороны.
    assert futures.entry_total == Decimal("9.00")
    assert futures.round_trip_total == Decimal("18.00")

    blocked = False

    try:
        calculate_round_trip_commission(
            entry_price=Decimal("95"),
            exit_price=Decimal("96"),
            quantity_units=Decimal("1"),
            parameters={
                "commission_model": (
                    MODEL_FINAM_FUTURES_CONFIGURED_V1
                ),
                "futures_broker_fee_per_contract_per_side": (
                    Decimal("1")
                ),
                "futures_fee_evidence_verified": False,
            },
        )
    except CommissionModelContractError as error:
        blocked = (
            str(error)
            == "futures_fee_evidence_not_verified"
        )

    assert blocked

    print("legacy_round_trip_commission=3.0")
    print(
        "equity_report_proxy_round_trip_commission="
        f"{equity.round_trip_total}"
    )
    print(
        "futures_configured_round_trip_commission="
        f"{futures.round_trip_total}"
    )
    print("futures_unverified_model_blocked=1")
    print(
        "VERDICT="
        "FINAM_COMMISSION_MODEL_V1_SELF_TEST_OK"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(self_test())
