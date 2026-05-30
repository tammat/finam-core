from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class PaperCostBreakdown:
    currency: str
    notional_rub: float
    broker_commission_rub: float
    exchange_commission_rub: float
    min_commission_rub: float
    commission_rub: float
    tax_rub: float
    net_cost_rub: float


class PaperCostModel:
    """
    Русский комментарий:
    Консервативная модель издержек PAPER-сделок.
    Все суммы считаются в рублях.
    v1.1:
    - broker commission RUB
    - exchange commission RUB
    - tax reserve RUB
    - net_cost_rub = commission_rub + tax_rub
    """

    def __init__(
        self,
        *,
        broker_rate: float | None = None,
        exchange_rate: float | None = None,
        min_commission_rub: float | None = None,
        tax_rate: float | None = None,
        tax_enabled: bool | None = None,
        currency: str | None = None,
    ) -> None:
        self.currency = str(currency or os.getenv("PAPER_CURRENCY", "RUB")).upper()

        self.broker_rate = float(
            os.getenv("PAPER_BROKER_COMMISSION_RATE", "0.0")
            if broker_rate is None
            else broker_rate
        )
        self.exchange_rate = float(
            os.getenv("PAPER_EXCHANGE_COMMISSION_RATE", "0.0")
            if exchange_rate is None
            else exchange_rate
        )
        self.min_commission_rub = float(
            os.getenv("PAPER_MIN_COMMISSION", "0.0")
            if min_commission_rub is None
            else min_commission_rub
        )
        self.tax_rate = float(
            os.getenv("PAPER_TAX_RATE", "0.0")
            if tax_rate is None
            else tax_rate
        )

        if tax_enabled is None:
            self.tax_enabled = os.getenv("PAPER_TAX_ENABLED", "0") == "1"
        else:
            self.tax_enabled = bool(tax_enabled)

    def calculate(
        self,
        *,
        price: float,
        qty: float,
        tax_base_rub: float | None = None,
    ) -> PaperCostBreakdown:
        notional_rub = abs(float(price) * float(qty))

        broker_commission_rub = notional_rub * self.broker_rate
        exchange_commission_rub = notional_rub * self.exchange_rate

        raw_commission_rub = broker_commission_rub + exchange_commission_rub
        commission_rub = max(raw_commission_rub, self.min_commission_rub)

        # Русский комментарий:
        # Налог корректно считается от реализованной прибыли, а не от оборота.
        # Поэтому здесь резервируем налог только при переданной налоговой базе.
        taxable_base = max(float(tax_base_rub or 0.0), 0.0)
        tax_rub = taxable_base * self.tax_rate if self.tax_enabled else 0.0

        net_cost_rub = commission_rub + tax_rub

        return PaperCostBreakdown(
            currency=self.currency,
            notional_rub=notional_rub,
            broker_commission_rub=broker_commission_rub,
            exchange_commission_rub=exchange_commission_rub,
            min_commission_rub=self.min_commission_rub,
            commission_rub=commission_rub,
            tax_rub=tax_rub,
            net_cost_rub=net_cost_rub,
        )
