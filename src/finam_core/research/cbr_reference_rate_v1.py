from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class CbrReferenceRate:
    """Официальный валютный курс Банка России."""

    currency_code: str
    cbr_code: str
    rate_date: date
    rate_value: Decimal


def select_rate_asof(
    rates: list[CbrReferenceRate],
    target_date: date,
) -> CbrReferenceRate:
    """
    Возвращает последний опубликованный курс,
    дата которого не превышает target_date.

    Future lookup запрещён.
    """

    eligible = [
        row
        for row in rates
        if row.rate_date <= target_date
    ]

    if not eligible:
        raise ValueError(
            "CBR_REFERENCE_RATE_ASOF_NOT_FOUND:"
            f"target_date={target_date}"
        )

    return max(
        eligible,
        key=lambda row: row.rate_date,
    )


def brz_tick_value_rub(
    *,
    tick_size: Decimal,
    lot_size: Decimal,
    usd_rub_rate: Decimal,
) -> Decimal:
    """
    Стоимость шага BR в рублях.

    Формула подтверждена на 13/13 сохранённых
    спецификациях BRZ6@RTSX.
    """

    if tick_size <= 0:
        raise ValueError("TICK_SIZE_MUST_BE_POSITIVE")

    if lot_size <= 0:
        raise ValueError("LOT_SIZE_MUST_BE_POSITIVE")

    if usd_rub_rate <= 0:
        raise ValueError("USD_RUB_RATE_MUST_BE_POSITIVE")

    return tick_size * lot_size * usd_rub_rate


def futures_price_delta_to_rub(
    *,
    price_delta: Decimal,
    quantity: Decimal,
    tick_size: Decimal,
    tick_value: Decimal,
) -> Decimal:
    """
    Перевод движения цены фьючерса в денежный PnL.

    quantity — количество контрактов.
    tick_value — стоимость одного tick для одного контракта.
    """

    if quantity <= 0:
        raise ValueError("QUANTITY_MUST_BE_POSITIVE")

    if tick_size <= 0:
        raise ValueError("TICK_SIZE_MUST_BE_POSITIVE")

    if tick_value <= 0:
        raise ValueError("TICK_VALUE_MUST_BE_POSITIVE")

    return (
        price_delta
        / tick_size
        * tick_value
        * quantity
    )
